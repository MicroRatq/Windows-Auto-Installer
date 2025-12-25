Set-StrictMode -Version 'Latest';
$ErrorActionPreference = 'Stop';
$(
	try {{
		$guid = '{guid}';
		$xml = "{active_folder}\${{guid}}.xml";
		$binary = "{active_folder}\${{guid}}.cip";
		Copy-Item -LiteralPath '{template_file}' -Destination $xml;
{set_rule_options}
		Merge-CIPolicy -PolicyPaths $xml -OutputFilePath $xml -Rules $(
			@(
				New-CIPolicyRule -FilePathRule 'C:\Windows\*';
				New-CIPolicyRule -FilePathRule 'C:\Program Files\*';
				New-CIPolicyRule -FilePathRule 'C:\Program Files (x86)\*';
{deny_rules}
			) | ForEach-Object -Process {{
				$_;
			}};
		);
		$doc = [xml]::new();
		$doc.Load( $xml );
		$nsmgr = [System.Xml.XmlNamespaceManager]::new( $doc.NameTable );
		$nsmgr.AddNamespace( 'pol', 'urn:schemas-microsoft-com:sipolicy' );
		$doc.SelectSingleNode( '/pol:SiPolicy/pol:PolicyID', $nsmgr ).InnerText = $guid;
		$doc.SelectSingleNode( '/pol:SiPolicy/pol:BasePolicyID', $nsmgr ).InnerText = $guid;
		$node = $doc.SelectSingleNode( '//pol:SigningScenario[@Value="12"]/pol:ProductSigners/pol:AllowedSigners', $nsmgr );
		$node.ParentNode.RemoveChild( $node );
		$doc.Save( $xml );
		ConvertFrom-CIPolicy -XmlFilePath $xml -BinaryFilePath $binary;
	}} catch {{
		$_;
	}}
) *>&1 | Out-String -Width 1KB -Stream >> 'C:\Windows\Setup\Scripts\Wdac.log';
