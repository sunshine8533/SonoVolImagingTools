# Simple Vivado script to program a SPI flash
#
# The board should be connected via a programming cable and powered prior to
# running. The programming file is specified by the variable
# "programming_files" in this example
#
# Run this script from a Vivado command prompt:
# vivado -mode batch -source program_spi.tcl
open_hw
connect_hw_server -url localhost:3121
current_hw_target [get_hw_targets]
open_hw_target
# Set the current Xilinx FPGA device. If more than one FPGA is in the JTAG
# chain, you may need to use the get_hw_devices command to help set the proper
# one with the current_hw_target command current_hw_device [lindex [get_hw_devices] 0]
# Set my_mem_device variable for the SPI flash device get_cfgmem_parts can be
# used to find the supported flash. See "help get_cfgmem_parts" in the Vivado
# Tcl Console when in the Hardware Manager for options which can help narrow
# the search. UG908 also lists supported SPI flash devices. Be sure to use the
# parts ending with _x1_x2_x4 for width x1, x2, and x4 and parts ending with
# _x1_x2_x4_x8 for Dual Quad SPI (x8 width).
set WORK_DIR ../../work/vivado/vivado_[clock format [clock seconds]  -format {%Y%m%d%H%M%S}]
file mkdir $WORK_DIR
set my_mem_device [lindex [get_cfgmem_parts {n25q128-1.8v-spi-x1_x2_x4}] 0]
# Set a variable to point the to BIN file to program
set programming_files C:/Users/JadTawil/Documents/KilN/Kintex/StandAlone_Beta1p_ECT/103008_Standalone_4Z_13_23mm_No_PRI_Vsampling_FX3_breakout_Ext_trig_BitfileID_V37.1_ECR-105_2017.09.15.mcs
# Create a hardware configuration memory object and associate it with the
# hardware device. Also, set a variable with which to point to this object
set my_hw_cfgmem [create_hw_cfgmem -hw_device \
[lindex [get_hw_devices] 0] -mem_dev $my_mem_device]
# Set the address range used for erasing to the size of the programming file
set_property PROGRAM.ADDRESS_RANGE {use_file} $my_hw_cfgmem
# Set the programming file to program into the SPI flash
set_property PROGRAM.FILES $programming_files $my_hw_cfgmem
# Set the termination of unused pins when programming the SPI flash
set_property PROGRAM.UNUSED_PIN_TERMINATION {pull-none} $my_hw_cfgmem
# Configure the hardware device with the programming bitstream
program_hw_devices [lindex [get_hw_devices] 0]
# Set programming options
# Do not perform a blank check, but erase, program and verify
set_property PROGRAM.BLANK_CHECK 0 $my_hw_cfgmem
set_property PROGRAM.ERASE 1 $my_hw_cfgmem
set_property PROGRAM.CFG_PROGRAM 1 $my_hw_cfgmem
set_property PROGRAM.VERIFY 1 $my_hw_cfgmem
# Now program the part
program_hw_cfgmem -hw_cfgmem $my_hw_cfgmem