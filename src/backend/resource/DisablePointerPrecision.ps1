$params = @{
	LiteralPath = 'Registry::HKU\DefaultUser\Control Panel\Mouse';
	Type = 'String';
	Value = 0;
	Force = $true;
};
Set-ItemProperty @params -Name 'MouseSpeed';
Set-ItemProperty @params -Name 'MouseThreshold1';
Set-ItemProperty @params -Name 'MouseThreshold2';
