# Rebuild the experimental variant and save reports for comparison with PR3.
set repo_root [file normalize [file join [file dirname [info script]] ../..]]
source [file join $repo_root fpga pipeline_experiment create_vivado_project.tcl]
set reports_dir [file join $repo_root vivado_pr3_pipeline reports]
file mkdir $reports_dir

# The experiment may have been edited since a previous run.
if {![string match "*Not started*" [get_property STATUS [get_runs impl_1]]]} {
    reset_run impl_1
}
if {![string match "*Not started*" [get_property STATUS [get_runs synth_1]]]} {
    reset_run synth_1
}
launch_runs synth_1 -jobs 2
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "PIPELINE_SYNTHESIS_STATUS: $synth_status"
if {![string match "*Complete*" $synth_status]} {
    error "Experimental synthesis failed; inspect vivado_pr3_pipeline/bnn_pr3_pipeline.runs/synth_1/runme.log"
}

launch_runs impl_1 -to_step route_design -jobs 2
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "PIPELINE_IMPLEMENTATION_STATUS: $impl_status"
if {![string match "*Complete*" $impl_status]} {
    error "Experimental implementation failed; inspect vivado_pr3_pipeline/bnn_pr3_pipeline.runs/impl_1/runme.log"
}

open_run impl_1
report_utilization -file [file join $reports_dir utilization_routed.rpt]
report_timing_summary -file [file join $reports_dir timing_routed.rpt]
report_route_status -file [file join $reports_dir route_status.rpt]
report_drc -file [file join $reports_dir drc_routed.rpt]
puts "PIPELINE_DONE: reports saved in $reports_dir"
