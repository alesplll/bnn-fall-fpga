# Create a separate project; do not replace the completed PR3 project.
set repo_root [file normalize [file join [file dirname [info script]] ../..]]
set project_dir [file join $repo_root vivado_pr3_pipeline]
set project_file [file join $project_dir bnn_pr3_pipeline.xpr]
set part xc7a100tcsg324-1

catch {close_sim}
catch {close_project}
if {[file exists $project_file]} {
    open_project $project_file
} else {
    create_project bnn_pr3_pipeline $project_dir -part $part
    set_property target_language Verilog [current_project]

    set core_file [file join $repo_root rtl bnn_classifier_pipelined.v]
    set top_file [file join $repo_root fpga fpga_top_pipelined.v]
    set tb_file [file join $repo_root fpga tb_fpga_top_pipelined.v]
    set xdc_file [file join $repo_root fpga clock_only.xdc]
    set mem_files [list]
    foreach name {
        weights_layerA_W.mem weights_layerA_b.mem
        weights_layerB_W.mem weights_layerB_b.mem
        tb_inputs_64.mem tb_expected_64.mem
    } {
        set path [file join $repo_root weights $name]
        if {![file exists $path]} {
            error "Missing memory file: $path"
        }
        lappend mem_files $path
    }

    add_files -fileset sources_1 [concat [list $core_file $top_file] $mem_files]
    set_property top fpga_top_pipelined [get_filesets sources_1]
    add_files -fileset sim_1 [list $tb_file]
    set_property top tb_fpga_top_pipelined [get_filesets sim_1]
    set_property xsim.simulate.runtime {10 us} [get_filesets sim_1]
    add_files -fileset constrs_1 [list $xdc_file]
    update_compile_order -fileset sources_1
    update_compile_order -fileset sim_1
}
puts "PIPELINE_PROJECT: $project_file"
