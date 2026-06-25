& {
	foreach( $letter in 'DEFGHIJKLMNOPQRSTUVWXYZ'.ToCharArray() ) {
		$exe = "${letter}:\PTAgent.exe";
		if( Test-Path -LiteralPath $exe ) {
			# https://kb.parallels.com/116161/
			# Install without any UI, don't reboot after install, and block until setup completes.
			Start-Process -FilePath $exe -ArgumentList '/install_silent' -Wait;
			return;
		}
	}
	'Parallels Tools image (prl-tools-win-*.iso) is not attached to this VM.';
} *>&1 | Out-String -Width 1KB -Stream >> 'C:\Windows\Setup\Scripts\ParallelsTools.log';
