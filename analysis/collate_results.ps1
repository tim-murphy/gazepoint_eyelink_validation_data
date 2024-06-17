# take a directory and write all CSV data to a new file

function printUsage
{
    $arg0 = Split-Path $PSCommandPath -Leaf
    echo "Usage: ${arg0} <data_dir> <out_csv> [<participant_id> [<participant_id> [...]]]"
}

if ($args.count -lt 2)
{
    printUsage
    exit 1
}

$data_dir = $args[0]
$out_csv = $args[1]

if ($args.count -gt 2)
{
    # clear the output file if it already exists
    New-Item -Name $out_csv -ItemType File -Force | Out-Null
    Clear-Content $out_csv

    for ($i = 2; $i -lt $args.count; $i++)
    {
        # pull out each ID and write it manually
        $id = [int]$args[$i]
        Get-Content $data_dir\$id.csv | Add-Content $out_csv
    }
}
else
{
    # just grab everything
    Get-Content (Get-ChildItem $data_dir\*.csv -Exclude *.stats.csv) | Set-Content $out_csv
}
