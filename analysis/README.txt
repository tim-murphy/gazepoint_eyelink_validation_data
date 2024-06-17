To run stats:

1. Download Qualtrics output CSV file
2. Run script `python simplify_qualtrix.py` on this file, save to `Qualtrics.csv`
3. Run script `powershell create_plots.ps1 | Tee-Object stats_output.log`

This will create multiple directories: one using all targets, one for "ideal" (optimal) targets only, and one for each correction modality with "ideal" targets. Graphs will be created per subject, per category (specs, eye colour, etc.), and per tracker setup. Stats will be printed to screen and saved in stats_output.log.

Stats output is all detailed in stats_output.log, which is included in this directory.