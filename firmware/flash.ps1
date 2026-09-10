# Flash the ATC RoIP Gateway over SWD (ST-LINK on header J2).
# Requires STM32CubeProgrammer:
#   https://www.st.com/en/development-tools/stm32cubeprog.html
param(
    [string]$Image = "build/atc-roip-gw.bin",
    [string]$Address = "0x08000000"
)

$cli = Get-Command STM32_Programmer_CLI -ErrorAction SilentlyContinue
if (-not $cli) {
    $default = "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    if (Test-Path $default) { $cli = $default }
    else {
        Write-Error "STM32_Programmer_CLI not found - install STM32CubeProgrammer."
        exit 1
    }
}
if (-not (Test-Path $Image)) {
    Write-Error "Image '$Image' not found - build first (see README.md)."
    exit 1
}

& $cli -c port=SWD mode=UR -w $Image $Address -v -rst
