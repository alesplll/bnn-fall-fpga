# Run synthesis and place-and-route, then save reports and a routed checkpoint.
# No bitstream is generated: there is no identified board or pinout.

set repo_root [file normalize [file join [file dirname [info script]] ..]]
set project_dir [file join $repo_root vivado_pr3]
set project_file [file join $project_dir bnn_pr3.xpr]
if {[file exists $project_file]} {
    catch {close_project}
    open_project $project_file
} else {
    source [file join $repo_root fpga create_vivado_project.tcl]
}

set reports_dir [file join $project_dir reports]
file mkdir $reports_dir

set synth_status [get_property STATUS [get_runs synth_1]]
if {![string match "*Complete*" $synth_status]} {
    launch_runs synth_1 -jobs 2
    wait_on_run synth_1
    set synth_status [get_property STATUS [get_runs synth_1]]
}
puts "PR3_SYNTHESIS_STATUS: $synth_status"
if {![string match "*Complete*" $synth_status]} {
    error "Synthesis did not complete; see the synth_1 run log"
}

set impl_status [get_property STATUS [get_runs impl_1]]
if {![string match "*Complete*" $impl_status]} {
    launch_runs impl_1 -to_step route_design -jobs 2
    wait_on_run impl_1
    set impl_status [get_property STATUS [get_runs impl_1]]
}
puts "PR3_IMPLEMENTATION_STATUS: $impl_status"
if {![string match "*Complete*" $impl_status]} {
    error "Implementation did not complete; see the impl_1 run log"
}

open_run impl_1
report_utilization -file [file join $reports_dir utilization_routed.rpt]
report_timing_summary -file [file join $reports_dir timing_routed.rpt]
report_route_status -file [file join $reports_dir route_status.rpt]
report_drc -file [file join $reports_dir drc_routed.rpt]
write_checkpoint -force [file join $reports_dir fpga_top_routed.dcp]

puts "PR3_DONE: routed design and reports saved in $reports_dir"
