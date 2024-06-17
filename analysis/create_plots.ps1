$projects = @("position", "validation")
$plots = @("vector") # can also have 'scatter' here too
$spectypes = @{
    'mf' = "*multifocal*"
    'sv' = "*single vision*"
    'bf' = "*bifocal*"
    'none' = "None"
    'cl' = "*Contact lenses*"
}

# XXX not being used at the moment
$colours = @{
    'dark_brown' = "Dark Brown"
    'brown' = "Brown"
    'hazel' = "Hazel"
    'blue' = "Blue"
    'green' = "Green"
}

# a bit of a hack to get blue vs. non-blue categories
$blueness = @{
    'blue' = "Blue"
    'non-blue' = "?[ar]*"
}

$darkness = @{
    'light' = "*e*"
    'dark' = "*Brown"
}

$panto = @(0..20)

$categories = @{
    'Correction' = $spectypes
    # 'EyeColour' = $blueness
    'EyeColour' = $darkness
    # 'Panto' = $panto # FIXME not using 
}

$runIdealStats = $True

# FIXME for faster processing for validation paper
# $projects = @("position")
$projects = @("validation")

# no data for these participants
$excluded_exp = @() # will be populated with excluded experiments

 # Note: this is required to create additional plots also
$CREATE_INDIVIDUAL_CAT_PLOTS = $True

# smoke test for python files
python -m py_compile (gci *.py)
if (-not $?)
{
    echo "ERROR: python code did not compile"
}

echo "Deleting previous records, if they exist."
$answer =$Host.UI.PromptForChoice("Confirm Please", "Are you sure you want to continue?", @("&Yes", "&No"), 0) 
if ($answer -eq 1)
{
    echo "Not continuing. Goodbye."
    exit
}

function doStats
{
    param (
        [Parameter(Mandatory=$True, Position=0)] [string] $proj,
        [Parameter(Mandatory=$False, Position=1)] [string] $target_file,
        [Parameter(Mandatory=$False, Position=2)] [string] $output_suffix
    )

    if (-not $target_file)
    {
        $target_file = ""
    }

    if (-not $output_suffix)
    {
        $output_suffix = ""
    }

    Remove-Item -Recurse -Force -ErrorAction Ignore "${proj}${output_suffix}" | out-null

    $qualtrics = "..\${proj}\Qualtrics.csv"

    $distance_cm = "65"
    if ($proj -eq "validation")
    {
        $distance_cm = "80"
    }

    echo "Processing $proj project"
    foreach($exp in (gci -Directory "..\${proj}"))
    {
        $exp_id = [int]$exp.Name
        $exp_record = import-csv "${qualtrics}" | Where-Object {$_.ID -eq $exp_id}

        # exclude contact lens - insufficient participants
        if ($exp_record.Correction -Match "Contact lens")
        {
            echo "  excluding $exp (contact lens subject)"
            $excluded_exp += $exp_id
            continue
        }

        $useTop = $True
        $useBottom = $True
        if ($proj -eq "position")
        {
            if ([int]$exp_record.ValidationErrorsTop -gt 3)
            {
                echo "  excluding $exp top data (too many validation errors)"
                $useTop = $False
            }

            if ([int]$exp_record.ValidationErrorsBottom -gt 3)
            {
                echo "  excluding $exp bottom data (too many validation errors)"
                $useBottom = $False
            }
        }

        if (-not ($useTop -or $useBottom))
        {
            echo "  all data for $exp excluded"
            $excluded_exp += $exp_id
            continue
        }

        echo "  processing experiment $exp"
        New-Item -ItemType Directory -Force -Path "${proj}${output_suffix}" | out-null

        if ($useTop -and $useBottom)
        {
            powershell ./collate_results.ps1 "../${proj}\${exp}" "${proj}${output_suffix}\${exp}.csv" | out-null
        }
        elseif ($useTop) # position project only
        {
            copy "..\${proj}\${exp}\gp3_top.csv" "${proj}${output_suffix}\${exp}.csv"
        }
        else # position project only
        {
            copy "..\${proj}\${exp}\gp3_bottom.csv" "${proj}${output_suffix}\${exp}.csv"
        }

        foreach($plot in $plots)
        {
            New-Item -ItemType Directory -Force -Path "${proj}${output_suffix}\plots" | out-null

            if ($CREATE_INDIVIDUAL_CAT_PLOTS)
            {
                python ./analyze_tracker_results.py "${proj}\${exp}.csv" "${plot}" "${distance_cm}" "${proj}${output_suffix}\plots\${exp}_${plot}.png" "${exp}" "${target_file}" | out-null
            }
        }
    }

    # put all of the participant data into one stats file
    $participantStats = "${proj}${output_suffix}\all.stats.csv"
    $firstRun = $True
    foreach($s in Get-ChildItem "${proj}${output_suffix}\plots\*.stats.csv")
    {
        if ($firstRun)
        {
            Get-Content "${s}" -Head 1 | Set-Content "${participantStats}"
            $firstRun = $False
        }

        Get-Content "${s}" | Select-Object -Skip 1 | Add-Content "${participantStats}"
    }

    echo ""
    echo "  Creating composite plots..."
    New-Item -ItemType Directory -Force -Path "${proj}${output_suffix}\all" | out-null
    New-Item -ItemType Directory -Force -Path "${proj}${output_suffix}\all\plots" | out-null

    # split by categories
    foreach ($cat in $categories.GetEnumerator())
    {
        $catname = $cat.Name
        $subcategories = $cat.Value
        echo "    ${catname}"

        $catdir = "${proj}${output_suffix}\all\${catname}"
        New-Item -ItemType Directory -Force -Path "${catdir}" | out-null

        foreach ($cattype in $subcategories.GetEnumerator())
        {
            $ids = ""

            # if an array
            $wildcard = $cattype
            $abbrev = $cattype

            if ($subcategories -is [Hashtable])
            {
                $wildcard = $cattype.Value
                $abbrev = $cattype.Name
            }

            echo "      ${abbrev}"

            foreach ($id in import-csv "${qualtrics}" | ? $catname -like $wildcard | select ID )
            {
                if (-not $excluded_exp.Contains([int]$id.ID))
                {
                    $ids += $id.ID + " "
                }
            }

            if ($ids -eq "")
            {
                echo "        - no data found (${catname} like ${wildcard})"
                continue
            }

            $new_csv = "${catdir}\${proj}_${abbrev}.csv"

            . powershell ./collate_results.ps1 "${proj}" "${new_csv}" $ids

            # add the spec type description to the file
            (Import-Csv "${new_csv}") | ForEach-Object `
            {
                $_.Label = "${abbrev} - " + $_.Label
                $_
            } | Export-Csv "${new_csv}" -NoTypeInformation

            foreach($plot in $plots)
            {
                New-Item -ItemType Directory -Force -Path "${catdir}\plots" | out-null
                python ./analyze_tracker_results.py "${new_csv}" "${plot}" "${distance_cm}" "${catdir}\plots\${proj}_${abbrev}_${plot}.png" "${abbrev}" "${target_file}" | out-null
            }
        }

        # everything by category
        echo "      all together"
        powershell ./collate_results.ps1 "${catdir}" "${catdir}\${proj}_all_cats.csv"
        foreach($plot in $plots)
        {
            python ./analyze_tracker_results.py "${catdir}\${proj}_all_cats.csv" "${plot}" "${distance_cm}" "${proj}${output_suffix}\all\plots\${proj}_${catname}_${plot}.png" "${catname}" "${target_file}" | out-null
        }
    }

    # everything
    echo "    everything"
    $allprojdata = "${proj}${output_suffix}\all\${proj}_all.csv"
    powershell ./collate_results.ps1 "${proj}${output_suffix}" "${allprojdata}"

    foreach($plot in $plots)
    {
        python ./analyze_tracker_results.py "${proj}${output_suffix}\all\${proj}_all.csv" "${plot}" "${distance_cm}" "${proj}${output_suffix}\all\plots\${proj}_${plot}.png" "None" "${target_file}" | out-null
    }

    # additional plots
    if ($CREATE_INDIVIDUAL_CAT_PLOTS) # needed to create $participantStats file
    {
        python ./create_extra_graphs.py "${qualtrics}" "${participantStats}" "${allprojdata}" "${proj}${output_suffix}" "${proj}"
    }
}

foreach($proj in $projects)
{
    # run stats for all
    echo " ********** Stats for all targets **********"
    doStats "${proj}"

    # calculate the 'ideal' target locations
    if ($proj -eq "position")
    {
        echo " ********** Calculate best targets **********"
        python .\create_target_stats.py "${proj}\all\plots\${proj}_vector.png.stats.csv" "..\${proj}\target_stats.csv" "${proj}"
        python .\cluster_targets.py "..\${proj}\target_stats.csv" "${proj}" "${proj}\best_targets.csv" "${proj}\all\plots\${proj}_cluster_targets.png" "${proj}"

        # run stats again for these ideal locations
        if ($runIdealStats)
        {
            echo " ********** Stats for ideal targets **********"
            doStats "${proj}" "${proj}\best_targets.csv" "_ideal"
        }

        # strip out the different correction modalities and run stats for those too
        foreach($corr in @('none', 'sv', 'mf'))
        {
            echo " ********** Calculate best targets - $corr **********"
            Get-Content "${proj}\all\plots\${proj}_Correction_vector.png.stats.csv" | Select -first 1 > "${proj}\all\plots\${proj}_Correction_vector_${corr}.png.stats.csv"
            Get-Content "${proj}\all\plots\${proj}_Correction_vector.png.stats.csv" | ? { $_ -like "*:: ${corr} - *" } >> "${proj}\all\plots\${proj}_Correction_vector_${corr}.png.stats.csv"

            # powershell hack - remove blank lines added by the write/append :(
            (gc "${proj}\all\plots\${proj}_Correction_vector_${corr}.png.stats.csv") | ? {$_.trim() -ne "" } | set-content "${proj}\all\plots\${proj}_Correction_vector_${corr}.png.stats.csv"

            # calculate the stats using this data subset
            python .\create_target_stats.py "${proj}\all\plots\${proj}_Correction_vector_${corr}.png.stats.csv" "..\${proj}\target_stats_$corr.csv" "${proj}"

            # and cluster
            python .\cluster_targets.py "..\${proj}\target_stats_$corr.csv" "${proj}" "${proj}\best_targets_$corr.csv" "${proj}\all\plots\${proj}_cluster_targets_${corr}.png" "${proj}"

            if ($runIdealStats)
            {
                echo " ********** Stats for ideal targets - $corr **********"
                doStats "${proj}" "${proj}\best_targets_$corr.csv" "_ideal_$corr"
            }
        }
    }
}

# EOF
