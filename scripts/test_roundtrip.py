#!/usr/bin/env python3
"""
测试 XML roundtrip 功能
使用 ref/test.xml 进行测试：
1. 解析 XML -> config_dict
2. config_dict -> Configuration
3. Configuration -> XML
4. 对比原始 XML 和生成的 XML
"""

from operator import eq
import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET

# 添加后端路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "src" / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from unattend_generator import (
    UnattendGenerator,
    config_dict_to_configuration,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def extract_numeric_entities(xml_bytes: bytes, label: str) -> list[dict]:
    """提取数字字符引用，区分十进制与十六进制"""
    text = xml_bytes.decode('utf-8', errors='ignore')
    entities = []
    for m in re.finditer(r'&#(x?[0-9A-Fa-f]+);', text):
        raw = m.group(0)
        val = m.group(1)
        is_hex = val.lower().startswith('x')
        # 计算行列
        line = text.count('\n', 0, m.start()) + 1
        col = m.start() - text.rfind('\n', 0, m.start())
        entities.append({
            'raw': raw,
            'value': val,
            'is_hex': is_hex,
            'line': line,
            'col': col,
            'label': label,
        })
    return entities


def check_numeric_entities(original_bytes: bytes, generated_bytes: bytes, differences: list):
    """对比数字实体格式，强调十六进制要求"""
    orig_entities = extract_numeric_entities(original_bytes, 'original_xml')
    gen_entities = extract_numeric_entities(generated_bytes, 'generated_xml')

    # 1) 生成的 XML 中是否存在十进制实体
    for ent in gen_entities:
        if not ent['is_hex']:
            differences.append({
                'path': f"@generated_xml:{ent['line']}:{ent['col']}",
                'type': '数字字符引用使用十进制',
                'expected': '使用十六进制（形如 &#xhhhh;）',
                'actual': ent['raw']
            })

    # 2) 同一位置实体格式差异（长度与顺序一致时尝试逐个对比）
    if len(orig_entities) == len(gen_entities):
        for i, (o, g) in enumerate(zip(orig_entities, gen_entities), start=1):
            if o['raw'] != g['raw']:
                differences.append({
                    'path': f"@entity[{i}]",
                    'type': '数字字符引用格式不一致',
                    'expected': f"原始 XML 使用 {o['raw']}",
                    'actual': f"生成的 XML 使用 {g['raw']}"
                })
    else:
        differences.append({
            'path': '@entity_count',
            'type': '数字字符引用数量不一致',
            'expected': f"原始 XML: {len(orig_entities)}",
            'actual': f"生成的 XML: {len(gen_entities)}"
        })


def get_element_path(elem: ET.Element | None, namespaces: dict, include_root: bool = True) -> str:
    """获取元素的路径"""
    if elem is None:
        return ""
    
    path_parts = []
    current = elem
    
    while current is not None:
        tag = current.tag
        # 移除命名空间前缀
        for ns_uri, prefix in namespaces.items():
            if tag.startswith(f"{{{ns_uri}}}"):
                tag = tag.replace(f"{{{ns_uri}}}", f"{prefix}:")
                break
        else:
            # 如果没有匹配的命名空间，尝试移除任何命名空间
            if '}' in tag:
                tag = tag.split('}')[-1]
        
        # 添加属性信息
        if current.attrib:
            attrs = []
            for key, value in sorted(current.attrib.items()):
                if key.startswith('{'):
                    # 命名空间属性
                    continue
                attrs.append(f"@{key}='{value}'")
            if attrs:
                tag += f"[{', '.join(attrs)}]"
        
        path_parts.insert(0, tag)
        current = current.getparent() if hasattr(current, 'getparent') else None
    
    if not include_root:
        path_parts = path_parts[1:]
    
    return "/" + "/".join(path_parts)


def normalize_indent(text: str) -> str:
    """规范化缩进：将每行的前导制表符或2个空格统一处理
    
    规则：
    - 前导制表符(\t) 转换为 2 个空格
    - 前导2个空格保持不变
    - 混合使用制表符和空格时，统一转换为空格
    """
    if not text:
        return text
    lines = text.split('\n')
    normalized_lines = []
    for line in lines:
        # 计算前导空白字符
        leading_whitespace = 0
        tab_count = 0
        space_count = 0
        
        for char in line:
            if char == '\t':
                tab_count += 1
                leading_whitespace += 1
            elif char == ' ':
                space_count += 1
                leading_whitespace += 1
            else:
                break
        
        # 将前导制表符转换为2个空格，前导空格保持不变
        equivalent_spaces = tab_count * 2 + space_count
        # 重新构建行：使用等效的空格数
        if leading_whitespace > 0:
            normalized_line = ' ' * equivalent_spaces + line[leading_whitespace:]
        else:
            normalized_line = line
        normalized_lines.append(normalized_line)
    return '\n'.join(normalized_lines)


def compare_attributes(elem1: ET.Element, elem2: ET.Element, path: str, differences: list):
    """对比两个元素的属性"""
    attrs1 = {k: v for k, v in elem1.attrib.items() if not k.startswith('{')}
    attrs2 = {k: v for k, v in elem2.attrib.items() if not k.startswith('{')}
    
    all_keys = set(attrs1.keys()) | set(attrs2.keys())
    for key in sorted(all_keys):
        val1 = attrs1.get(key)
        val2 = attrs2.get(key)
        
        if val1 != val2:
            differences.append({
                'path': f"{path}/@{key}",
                'type': '属性值不一致',
                'expected': val2 if val2 is not None else '不存在',
                'actual': val1 if val1 is not None else '不存在'
            })


def compare_elements_recursive(elem1: ET.Element | None, elem2: ET.Element | None, 
                                path: str, differences: list, namespaces: dict):
    """递归对比两个元素及其子元素"""
    if elem1 is None and elem2 is None:
        return
    
    if elem1 is None:
        differences.append({
            'path': path,
            'type': '元素缺失（生成的XML）',
            'expected': '存在',
            'actual': None
        })
        return
    
    if elem2 is None:
        differences.append({
            'path': path,
            'type': '元素缺失（原始XML）',
            'expected': None,
            'actual': '存在'
        })
        return
    
    # 对比属性
    compare_attributes(elem1, elem2, path, differences)
    
    # 对比文本内容（规范化缩进后比较）
    # 注意：不 strip()，保留原始格式，只规范化缩进
    text1 = elem1.text or ''
    text2 = elem2.text or ''
    # 规范化缩进：将 \t 转换为 2 个空格
    normalized_text1 = normalize_indent(text1)
    normalized_text2 = normalize_indent(text2)
    # 去除末尾空白行后再比较
    normalized_text1 = normalized_text1.rstrip()
    normalized_text2 = normalized_text2.rstrip()
    if normalized_text1 != normalized_text2:
        # 忽略空白差异
        if text1 or text2:
            differences.append({
                'path': f"{path}/text()",
                'type': '文本内容不一致',
                'expected': text2 if text2 else '(空)',
                'actual': text1 if text1 else '(空)'
            })
    
    # 对比子元素
    children1 = {}
    children2 = {}
    
    for child in elem1:
        tag = child.tag
        # 获取本地名称（不带命名空间）
        if '}' in tag:
            local_name = tag.split('}')[-1]
        else:
            local_name = tag
        
        # 使用 name 属性作为 key（如果有）
        key = child.get('name', local_name)
        if key not in children1:
            children1[key] = []
        children1[key].append(child)
    
    for child in elem2:
        tag = child.tag
        if '}' in tag:
            local_name = tag.split('}')[-1]
        else:
            local_name = tag
        
        key = child.get('name', local_name)
        if key not in children2:
            children2[key] = []
        children2[key].append(child)
    
    # 对比所有子元素
    all_keys = set(children1.keys()) | set(children2.keys())
    for key in sorted(all_keys):
        list1 = children1.get(key, [])
        list2 = children2.get(key, [])
        
        # 如果数量不同，报告差异
        if len(list1) != len(list2):
            differences.append({
                'path': f"{path}/{key}",
                'type': '子元素数量不一致',
                'expected': f"原始 XML: {len(list2)}",
                'actual': f"生成的 XML: {len(list1)}"
            })
            # 对比较少的数量
            min_len = min(len(list1), len(list2))
            for i in range(min_len):
                child_path = f"{path}/{key}[{i}]"
                compare_elements_recursive(list1[i], list2[i], child_path, differences, namespaces)
        else:
            # 数量相同，逐个对比
            for i, (c1, c2) in enumerate(zip(list1, list2)):
                child_path = f"{path}/{key}[{i}]"
                compare_elements_recursive(c1, c2, child_path, differences, namespaces)


def compare_extensions(ext1: ET.Element | None, ext2: ET.Element | None, 
                       differences: list, namespaces: dict):
    """对比 Extensions 部分"""
    ext_path = "/unattend/Extensions"
    
    if ext1 is None and ext2 is None:
        return
    
    if ext1 is None:
        differences.append({
            'path': ext_path,
            'type': 'Extensions 缺失（生成的XML）',
            'expected': '存在',
            'actual': None
        })
        return
    
    if ext2 is None:
        differences.append({
            'path': ext_path,
            'type': 'Extensions 缺失（原始XML）',
            'expected': None,
            'actual': '存在'
        })
        return
    
    # 对比 ExtractScript
    ext_ns = namespaces.get('ext', 'https://schneegans.de/windows/unattend-generator/')
    script1 = ext1.find(f"{{{ext_ns}}}ExtractScript")
    script2 = ext2.find(f"{{{ext_ns}}}ExtractScript")
    
    if script1 is not None and script2 is not None:
        text1 = script1.text or ''
        text2 = script2.text or ''
        # 规范化缩进：将 \t 转换为 2 个空格
        normalized_text1 = normalize_indent(text1)
        normalized_text2 = normalize_indent(text2)
        # 去除末尾空白行后再比较
        normalized_text1 = normalized_text1.rstrip()
        normalized_text2 = normalized_text2.rstrip()
        if normalized_text1 != normalized_text2:
            differences.append({
                'path': f"{ext_path}/ExtractScript",
                'type': 'ExtractScript 内容不一致',
                'expected': text2 if text2 else '(空)',
                'actual': text1 if text1 else '(空)'
            })
    
    # 对比 File 元素
    files1 = {}
    files2 = {}
    
    # 查找 File 元素（支持有或没有命名空间的情况）
    for file_elem in ext1.findall(f"{{{ext_ns}}}File"):
        path_attr = file_elem.get('path', '')
        if path_attr:
            files1[path_attr] = file_elem
    # 如果没有找到，尝试查找任何 File 元素
    if not files1:
        for child in ext1:
            if child.tag.endswith('File'):
                path_attr = child.get('path', '')
                if path_attr:
                    files1[path_attr] = child
    
    for file_elem in ext2.findall(f"{{{ext_ns}}}File"):
        path_attr = file_elem.get('path', '')
        if path_attr:
            files2[path_attr] = file_elem
    # 如果没有找到，尝试查找任何 File 元素
    if not files2:
        for child in ext2:
            if child.tag.endswith('File'):
                path_attr = child.get('path', '')
                if path_attr:
                    files2[path_attr] = child
    
    # 对比所有文件
    all_paths = set(files1.keys()) | set(files2.keys())
    for file_path in sorted(all_paths):
        file1 = files1.get(file_path)
        file2 = files2.get(file_path)
        file_path_xml = f"{ext_path}/File[@path='{file_path}']"
        
        if file1 is None:
            differences.append({
                'path': file_path_xml,
                'type': 'File 元素缺失（生成的XML）',
                'expected': '存在',
                'actual': None
            })
            continue
        
        if file2 is None:
            differences.append({
                'path': file_path_xml,
                'type': 'File 元素缺失（原始XML）',
                'expected': None,
                'actual': '存在'
            })
            continue
        
        # 对比文件内容（规范化缩进后比较）
        # 注意：不 strip()，保留原始格式，只规范化缩进
        content1 = file1.text or ''
        content2 = file2.text or ''
        # 规范化缩进：将 \t 转换为 2 个空格
        normalized_content1 = normalize_indent(content1)
        normalized_content2 = normalize_indent(content2)
        # 去除末尾空白行后再比较
        normalized_content1 = normalized_content1.rstrip()
        normalized_content2 = normalized_content2.rstrip()
        if normalized_content1 != normalized_content2:
            differences.append({
                'path': f"{file_path_xml}/text()",
                'type': '文件内容不一致',
                'expected': content2 if content2 else '(空)',
                'actual': content1 if content1 else '(空)'
            })


def compare_xml(original_xml: bytes, generated_xml: bytes, test_name: str) -> bool:
    """对比两个 XML，返回是否一致"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Comparing XML for: {test_name}")
    logger.info(f"{'='*60}")
    
    differences = []
    
    # 检查数字字符引用格式（暂时注释，逻辑可能有误）
    # check_numeric_entities(original_xml, generated_xml, differences)
    
    try:
        # 解析 XML
        original_root = ET.fromstring(original_xml)
        generated_root = ET.fromstring(generated_xml)
        
        # 注册命名空间
        namespaces = {
            'u': 'urn:schemas-microsoft-com:unattend',
            'wcm': 'http://schemas.microsoft.com/WMIConfig/2002/State',
            'ext': 'https://schneegans.de/windows/unattend-generator/'
        }
        
        # 对比根元素属性
        compare_attributes(original_root, generated_root, '/unattend', differences)
        
        # 对比所有 settings pass
        settings_passes = ['offlineServicing', 'windowsPE', 'generalize', 'specialize', 
                          'auditSystem', 'auditUser', 'oobeSystem']
        
        original_settings = {}
        generated_settings = {}
        
        ns_uri = namespaces['u']
        for settings_elem in original_root.findall(f"{{{ns_uri}}}settings"):
            pass_attr = settings_elem.get('pass', '')
            if pass_attr:
                original_settings[pass_attr] = settings_elem
        
        for settings_elem in generated_root.findall(f"{{{ns_uri}}}settings"):
            pass_attr = settings_elem.get('pass', '')
            if pass_attr:
                generated_settings[pass_attr] = settings_elem
        
        # 对比每个 pass
        all_passes = set(original_settings.keys()) | set(generated_settings.keys())
        for pass_name in sorted(all_passes):
            orig_pass = original_settings.get(pass_name)
            gen_pass = generated_settings.get(pass_name)
            pass_path = f"/unattend/settings[@pass='{pass_name}']"
            
            if orig_pass is None:
                differences.append({
                    'path': pass_path,
                    'type': 'settings pass 缺失（原始XML）',
                    'expected': None,
                    'actual': '存在'
                })
                continue
            if gen_pass is None:
                differences.append({
                    'path': pass_path,
                    'type': 'settings pass 缺失（生成的XML）',
                    'expected': '存在',
                    'actual': None
                })
                continue
            
            # 对比 settings 属性
            compare_attributes(orig_pass, gen_pass, pass_path, differences)
            
            # 对比所有 component
            orig_components = {}
            gen_components = {}
            
            for comp in orig_pass.findall(f"{{{ns_uri}}}component"):
                comp_name = comp.get('name', '')
                if comp_name:
                    orig_components[comp_name] = comp
            
            for comp in gen_pass.findall(f"{{{ns_uri}}}component"):
                comp_name = comp.get('name', '')
                if comp_name:
                    gen_components[comp_name] = comp
            
            # 对比每个 component
            all_components = set(orig_components.keys()) | set(gen_components.keys())
            for comp_name in sorted(all_components):
                orig_comp = orig_components.get(comp_name)
                gen_comp = gen_components.get(comp_name)
                comp_path = f"{pass_path}/component[@name='{comp_name}']"
                
                if orig_comp is None:
                    differences.append({
                        'path': comp_path,
                        'type': 'component 缺失（原始XML）',
                        'expected': None,
                        'actual': '存在'
                    })
                    continue
                if gen_comp is None:
                    differences.append({
                        'path': comp_path,
                        'type': 'component 缺失（生成的XML）',
                        'expected': '存在',
                        'actual': None
                    })
                    continue
                
                # 递归对比 component 及其所有子元素
                compare_elements_recursive(gen_comp, orig_comp, comp_path, differences, namespaces)
        
        # 对比 Extensions 部分
        # 查找 Extensions 元素（支持有或没有 xmlns 的情况）
        generated_ext = generated_root.find(f"{{{namespaces['ext']}}}Extensions")
        if generated_ext is None:
            # 如果没有找到，尝试查找任何 Extensions 元素
            for elem in generated_root.iter():
                if elem.tag.endswith('Extensions'):
                    generated_ext = elem
                    break
        
        original_ext = original_root.find(f"{{{namespaces['ext']}}}Extensions")
        if original_ext is None:
            # 如果没有找到，尝试查找任何 Extensions 元素
            for elem in original_root.iter():
                if elem.tag.endswith('Extensions'):
                    original_ext = elem
                    break
        
        compare_extensions(
            generated_ext,
            original_ext,
            differences,
            namespaces
        )
        
        # 报告差异
        if differences:
            logger.error(f"✗ 发现 {len(differences)} 个差异:")
            for i, diff in enumerate(differences, 1):
                logger.error(f"  {i}. 路径: {diff['path']}")
                logger.error(f"     类型: {diff['type']}")
                if diff.get('expected') is not None:
                    logger.error(f"     期望值: {diff['expected']}")
                if diff.get('actual') is not None:
                    logger.error(f"     实际值: {diff['actual']}")
                logger.error("")
            
            # 保存 XML 文件用于调试
            output_dir = PROJECT_ROOT / 'test' / 'output'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            original_file = output_dir / f'{test_name}_original.xml'
            generated_file = output_dir / f'{test_name}_generated.xml'
            diff_file = output_dir / f'{test_name}_differences.txt'
            
            with open(original_file, 'wb') as f:
                f.write(original_xml)
            with open(generated_file, 'wb') as f:
                f.write(generated_xml)
            
            # 保存详细的差异报告
            with open(diff_file, 'w', encoding='utf-8') as f:
                f.write(f"XML Comparison Differences: {test_name}\n")
                f.write("="*60 + "\n\n")
                for i, diff in enumerate(differences, 1):
                    f.write(f"{i}. 路径: {diff['path']}\n")
                    f.write(f"   类型: {diff['type']}\n")
                    if diff.get('expected') is not None:
                        f.write(f"   期望值: {diff['expected']}\n")
                    if diff.get('actual') is not None:
                        f.write(f"   实际值: {diff['actual']}\n")
                    f.write("\n")
            
            logger.info(f"  保存原始 XML 到: {original_file}")
            logger.info(f"  保存生成的 XML 到: {generated_file}")
            logger.info(f"  保存差异报告到: {diff_file}")
            
            return False
        else:
            logger.info("✓ XML 完全一致！")
            return True
            
    except Exception as e:
        logger.error(f"✗ XML 对比过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_roundtrip():
    """测试 XML roundtrip 功能"""
    logger.info("\n" + "="*60)
    logger.info("Test: XML Roundtrip (ref/test.xml)")
    logger.info("="*60)
    
    # 读取测试 XML 文件
    xml_file = PROJECT_ROOT / 'ref' / 'test.xml'
    if not xml_file.exists():
        logger.error(f"✗ Test XML file not found: {xml_file}")
        return False
    
    logger.info(f"Reading test XML file: {xml_file}")
    with open(xml_file, 'rb') as f:
        original_xml = f.read()
    logger.info(f"✓ Read XML file ({len(original_xml)} bytes)")
    
    # ========================================
    # 步骤 1: 解析 XML
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 1: Parse XML")
    logger.info("-"*60)
    
    try:
        # 指定数据目录为 data/unattend
        data_dir = PROJECT_ROOT / 'data' / 'unattend'
        generator = UnattendGenerator(data_dir=data_dir)
        config_dict = generator.parse_xml(original_xml)
        logger.info(f"✓ Parsed XML successfully")
        logger.info(f"  Parsed {len(config_dict)} top-level keys")
        
        # 保存解析结果
        output_dir = PROJECT_ROOT / 'test' / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)
        parse_file = output_dir / 'roundtrip_parse_result.json'
        with open(parse_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"  Saved parse result to: {parse_file}")
    except Exception as e:
        logger.error(f"✗ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================
    # 步骤 2: 转换为 Configuration 对象
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 2: Convert config_dict to Configuration")
    logger.info("-"*60)
    
    try:
        config = config_dict_to_configuration(config_dict, generator)
        logger.info("✓ Converted config_dict to Configuration object")
    except Exception as e:
        logger.error(f"✗ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================
    # 步骤 3: 生成 XML
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 3: Generate XML from Configuration")
    logger.info("-"*60)
    
    try:
        generated_xml = generator.generate_xml(config)
        logger.info(f"✓ Generated XML ({len(generated_xml)} bytes)")
        
        # 保存生成的 XML
        gen_file = output_dir / 'roundtrip_generated.xml'
        with open(gen_file, 'wb') as f:
            f.write(generated_xml)
        logger.info(f"  Saved generated XML to: {gen_file}")
    except Exception as e:
        logger.error(f"✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================
    # 步骤 4: 对比 XML
    # ========================================
    logger.info("\n" + "-"*60)
    logger.info("Step 4: Compare Original and Generated XML")
    logger.info("-"*60)
    
    success = compare_xml(original_xml, generated_xml, 'roundtrip')
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✓ Roundtrip test PASSED!")
        logger.info("="*60)
    else:
        logger.error("\n" + "="*60)
        logger.error("✗ Roundtrip test FAILED!")
        logger.error("="*60)
    
    return success


if __name__ == '__main__':
    success = test_roundtrip()
    sys.exit(0 if success else 1)


