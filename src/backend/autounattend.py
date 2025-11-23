#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
autounattend.xml生成模块
参考: https://github.com/cschneegans/unattend-generator
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, Optional

class AutounattendGenerator:
    """autounattend.xml生成器"""
    
    def __init__(self):
        self.namespaces = {
            '': 'urn:schemas-microsoft-com:unattend',
            'wcm': 'http://schemas.microsoft.com/WMIConfig/2002/State',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
    
    def generate(self, config: Dict[str, Any]) -> str:
        """
        生成autounattend.xml
        
        Args:
            config: 配置字典，包含所有配置选项
        
        Returns:
            XML字符串
        """
        # 创建根元素
        root = ET.Element('unattend', {
            'xmlns': self.namespaces[''],
            'xmlns:wcm': self.namespaces['wcm'],
            'xmlns:xsi': self.namespaces['xsi']
        })
        
        # 添加各个配置阶段
        self._add_settings_pass(root, 'windowsPE', config)
        self._add_settings_pass(root, 'offlineServicing', config)
        self._add_settings_pass(root, 'generalize', config)
        self._add_settings_pass(root, 'specialize', config)
        self._add_settings_pass(root, 'oobeSystem', config)
        
        # 格式化XML
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
    
    def _add_settings_pass(self, root: ET.Element, pass_name: str, config: Dict[str, Any]):
        """添加配置阶段"""
        pass_elem = ET.SubElement(root, pass_name)
        
        if pass_name == 'windowsPE':
            self._add_windowspe_settings(pass_elem, config)
        elif pass_name == 'specialize':
            self._add_specialize_settings(pass_elem, config)
        elif pass_name == 'oobeSystem':
            self._add_oobe_settings(pass_elem, config)
        # 其他阶段可以根据需要添加
    
    def _add_windowspe_settings(self, pass_elem: ET.Element, config: Dict[str, Any]):
        """添加WindowsPE阶段设置"""
        # 组件配置
        component = ET.SubElement(pass_elem, 'component', {
            'name': 'Microsoft-Windows-Setup',
            'processorArchitecture': 'amd64',
            'publicKeyToken': '31bf3856ad364e35',
            'language': 'neutral',
            'versionScope': 'nonSxS'
        })
        
        # 用户数据
        user_data = ET.SubElement(component, 'UserData')
        accept_eula = ET.SubElement(user_data, 'AcceptEula')
        accept_eula.text = 'true'
        
        # 产品密钥（可选）
        if config.get('product_key'):
            product_key = ET.SubElement(user_data, 'ProductKey')
            key_elem = ET.SubElement(product_key, 'Key')
            key_elem.text = config['product_key']
            will_show_ui = ET.SubElement(product_key, 'WillShowUI')
            will_show_ui.text = 'OnError'
        
        # 磁盘配置
        disk_config = ET.SubElement(component, 'DiskConfiguration')
        disk = ET.SubElement(disk_config, 'Disk', {'wcm:action': 'add'})
        disk_id = ET.SubElement(disk, 'DiskID')
        disk_id.text = '0'
        will_wipe_disk = ET.SubElement(disk, 'WillWipeDisk')
        will_wipe_disk.text = 'true'
        
        create_partitions = ET.SubElement(disk, 'CreatePartitions')
        create_partition = ET.SubElement(create_partitions, 'CreatePartition', {'wcm:action': 'add'})
        order = ET.SubElement(create_partition, 'Order')
        order.text = '1'
        size = ET.SubElement(create_partition, 'Size')
        size.text = '500'
        type_elem = ET.SubElement(create_partition, 'Type')
        type_elem.text = 'EFI'
        
        create_partition2 = ET.SubElement(create_partitions, 'CreatePartition', {'wcm:action': 'add'})
        order2 = ET.SubElement(create_partition2, 'Order')
        order2.text = '2'
        size2 = ET.SubElement(create_partition2, 'Size')
        size2.text = '100'
        type_elem2 = ET.SubElement(create_partition2, 'Type')
        type_elem2.text = 'MSR'
        
        create_partition3 = ET.SubElement(create_partitions, 'CreatePartition', {'wcm:action': 'add'})
        order3 = ET.SubElement(create_partition3, 'Order')
        order3.text = '3'
        extend = ET.SubElement(create_partition3, 'Extend')
        extend.text = 'true'
        type_elem3 = ET.SubElement(create_partition3, 'Type')
        type_elem3.text = 'Primary'
        
        modify_partitions = ET.SubElement(disk, 'ModifyPartitions')
        modify_partition1 = ET.SubElement(modify_partitions, 'ModifyPartition', {'wcm:action': 'add'})
        active1 = ET.SubElement(modify_partition1, 'Active')
        active1.text = 'true'
        format1 = ET.SubElement(modify_partition1, 'Format')
        format1.text = 'FAT32'
        label1 = ET.SubElement(modify_partition1, 'Label')
        label1.text = 'System'
        order_m1 = ET.SubElement(modify_partition1, 'Order')
        order_m1.text = '1'
        partition_id1 = ET.SubElement(modify_partition1, 'PartitionID')
        partition_id1.text = '1'
        
        modify_partition3 = ET.SubElement(modify_partitions, 'ModifyPartition', {'wcm:action': 'add'})
        format3 = ET.SubElement(modify_partition3, 'Format')
        format3.text = 'NTFS'
        label3 = ET.SubElement(modify_partition3, 'Label')
        label3.text = 'Windows'
        order_m3 = ET.SubElement(modify_partition3, 'Order')
        order_m3.text = '3'
        partition_id3 = ET.SubElement(modify_partition3, 'PartitionID')
        partition_id3.text = '3'
        
        # 镜像安装
        image_install = ET.SubElement(component, 'ImageInstall')
        os_image = ET.SubElement(image_install, 'OSImage')
        install_to = ET.SubElement(os_image, 'InstallTo')
        disk_id_install = ET.SubElement(install_to, 'DiskID')
        disk_id_install.text = '0'
        partition_id_install = ET.SubElement(install_to, 'PartitionID')
        partition_id_install.text = '3'
        
        install_from = ET.SubElement(os_image, 'InstallFrom')
        meta_data = ET.SubElement(install_from, 'MetaData', {'wcm:action': 'add'})
        key = ET.SubElement(meta_data, 'Key')
        key.text = '/IMAGE/NAME'
        value = ET.SubElement(meta_data, 'Value')
        value.text = 'Windows'
    
    def _add_specialize_settings(self, pass_elem: ET.Element, config: Dict[str, Any]):
        """添加specialize阶段设置"""
        # 计算机名
        component = ET.SubElement(pass_elem, 'component', {
            'name': 'Microsoft-Windows-Shell-Setup',
            'processorArchitecture': 'amd64',
            'publicKeyToken': '31bf3856ad364e35',
            'language': 'neutral',
            'versionScope': 'nonSxS'
        })
        
        if config.get('computer_name'):
            computer_name = ET.SubElement(component, 'ComputerName')
            computer_name.text = config['computer_name']
        
        # 时区
        if config.get('timezone'):
            time_zone = ET.SubElement(component, 'TimeZone')
            time_zone.text = config['timezone']
        
        # 可选功能：命令行和注册表配置接口预留
        if config.get('options', {}).get('disableHibernation'):
            # TODO: 实现关闭休眠的注册表配置
            pass
        
        if config.get('options', {}).get('kmsActivate'):
            # TODO: 实现KMS激活的注册表配置
            pass
        
        if config.get('options', {}).get('pauseUpdates'):
            # TODO: 实现暂停Windows更新的注册表配置
            pass
        
        if config.get('options', {}).get('setPowerPlan'):
            # TODO: 实现电源计划设置的注册表配置
            pass
    
    def _add_oobe_settings(self, pass_elem: ET.Element, config: Dict[str, Any]):
        """添加OOBE阶段设置"""
        component = ET.SubElement(pass_elem, 'component', {
            'name': 'Microsoft-Windows-Shell-Setup',
            'processorArchitecture': 'amd64',
            'publicKeyToken': '31bf3856ad364e35',
            'language': 'neutral',
            'versionScope': 'nonSxS'
        })
        
        # 用户账户
        user_accounts = ET.SubElement(component, 'UserAccounts')
        local_accounts = ET.SubElement(user_accounts, 'LocalAccounts')
        
        if config.get('username') and config.get('password'):
            local_account = ET.SubElement(local_accounts, 'LocalAccount', {'wcm:action': 'add'})
            password = ET.SubElement(local_account, 'Password')
            value = ET.SubElement(password, 'Value')
            value.text = config['password']
            plain_text = ET.SubElement(password, 'PlainText')
            plain_text.text = 'false'
            description = ET.SubElement(local_account, 'Description')
            description.text = config.get('username', 'User')
            display_name = ET.SubElement(local_account, 'DisplayName')
            display_name.text = config.get('username', 'User')
            group = ET.SubElement(local_account, 'Group')
            group.text = 'Administrators'
            name = ET.SubElement(local_account, 'Name')
            name.text = config['username']
        
        # OOBE设置
        oobe = ET.SubElement(component, 'OOBE')
        hide_eula_page = ET.SubElement(oobe, 'HideEULAPage')
        hide_eula_page.text = 'true'
        hide_oem_registration_screen = ET.SubElement(oobe, 'HideOEMRegistrationScreen')
        hide_oem_registration_screen.text = 'true'
        hide_online_account_screens = ET.SubElement(oobe, 'HideOnlineAccountScreens')
        hide_online_account_screens.text = 'true'
        hide_wireless_setup_in_oobe = ET.SubElement(oobe, 'HideWirelessSetupInOOBE')
        hide_wireless_setup_in_oobe.text = 'true'
        network_location = ET.SubElement(oobe, 'NetworkLocation')
        network_location.text = 'Home'
        protect_your_pc = ET.SubElement(oobe, 'ProtectYourPC')
        protect_your_pc.text = '1'
        skip_user_oobe = ET.SubElement(oobe, 'SkipUserOOBE')
        skip_user_oobe.text = 'true'
        skip_machine_oobe = ET.SubElement(oobe, 'SkipMachineOOBE')
        skip_machine_oobe.text = 'true'
        
        # 可选功能：删除defaultuser0
        if config.get('options', {}).get('removeDefaultUser'):
            # TODO: 实现删除defaultuser0的命令行配置
            first_logon_commands = ET.SubElement(component, 'FirstLogonCommands')
            synchronous_command = ET.SubElement(first_logon_commands, 'SynchronousCommand', {'wcm:action': 'add'})
            command_line = ET.SubElement(synchronous_command, 'CommandLine')
            # 删除defaultuser0的命令
            command_line.text = 'net user defaultuser0 /delete'
            description_cmd = ET.SubElement(synchronous_command, 'Description')
            description_cmd.text = 'Delete defaultuser0'
            order_cmd = ET.SubElement(synchronous_command, 'Order')
            order_cmd.text = '1'
            requires_user_input = ET.SubElement(synchronous_command, 'RequiresUserInput')
            requires_user_input.text = 'false'
        
        # 可选功能：移除快速访问中文件夹
        if config.get('options', {}).get('removeQuickAccess'):
            # TODO: 实现移除快速访问的命令行或注册表配置
            pass

