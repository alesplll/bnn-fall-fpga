set repo_root [file normalize [file join [file dirname [info script]] ../..]]
source [file join $repo_root fpga pipeline_experiment create_vivado_project.tcl]
set_property top tb_fpga_top_pipelined [get_filesets sim_1]
set_property xsim.simulate.runtime {10 us} [get_filesets sim_1]
puts "PIPELINE_SIMULATION_TOP: [get_property top [get_filesets sim_1]]"
launch_simulation -simset sim_1 -mode behavioral
