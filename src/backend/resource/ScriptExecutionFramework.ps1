& {{
	[float] $complete = 0;
	[float] $increment = 100 / $scripts.Count;
	foreach( $script in $scripts ) {{
		Write-Progress -Activity '{activity} Do not close this window.' -PercentComplete $complete;
		'*** Will now execute command «{{0}}».' -f $(
			$str = $script.ToString().Trim() -replace '\s+', ' ';
			$max = 100;
			if( $str.Length -le $max ) {{
				$str;
			}} else {{
				$str.Substring( 0, $max - 1 ) + '…';
			}}
		);
		$start = [datetime]::Now;
		& $script;
		'*** Finished executing command after {{0:0}} ms.' -f [datetime]::Now.Subtract( $start ).TotalMilliseconds;
		"`r`n" * 3;
		$complete += $increment;
	}}
}} *>&1 | Out-String -Width 1KB -Stream >> "{log_file}";
