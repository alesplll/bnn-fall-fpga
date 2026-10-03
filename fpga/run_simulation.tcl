# Open the PR3 project and start the PR3 testbench, even if an older XSim
# session is still visible in Vivado.

set repo_root [file normalize [file join [file dirname [info script]] ..]]
set project_file [file join $repo_root vivado_pr3 bnn_pr3.xpr]
if {![file exists $project_file]} {
    error "PR3 project not found: $project_file. Run fpga/run_implementation.tcl first."
}

catch {close_sim}
catch {close_project}
open_project $project_file

set tb_file [file join $repo_root fpga tb_fpga_top.v]
if {![file exists $tb_file]} {
    error "PR3 testbench not found: $tb_file"
}
set tb_added 0
foreach source_file [get_files -quiet -of_objects [get_filesets sim_1]] {
    if {[file normalize $source_file] eq [file normalize $tb_file]} {
        set tb_added 1
    }
}
if {!$tb_added} {
    add_files -fileset sim_1 [list $tb_file]
}
update_compile_order -fileset sim_1
set_property top tb_fpga_top [get_filesets sim_1]
set_property xsim.simulate.runtime {6 us} [get_filesets sim_1]
puts "PR3_SIMULATION_TOP: [get_property top [get_filesets sim_1]]"
launch_simulation -simset sim_1 -mode behavioral
