try {{
	$bytes = Get-Content -LiteralPath '{getter_file}' -Raw | Invoke-Expression;
	[System.IO.File]::WriteAllBytes( '{image_file}', $bytes );
}} catch {{
	$_;
}}
