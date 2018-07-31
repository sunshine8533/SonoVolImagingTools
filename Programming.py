'''
Program iBMC with Lattice Diamond shell command

Example:
ibmc_Programming.bat
set %LSC_INI_PATH%=
set %LSC_DIAMOND%=true
set %TCL_LIBRARY%=d:\lscc\diamond\3.8_x64\tcltk\lib\tcl8.5
set %FOUNDRY%=d:\lscc\diamond\3.8_x64\ispfpga
set %PATH%=%FOUNDRY%\bin\nt64;%PATH%
d:\lscc\diamond\3.8_x64\bin\nt64\pnmainc.exe ibmc.tcl > output.txt

'''
        

import subprocess
import os
from TestPreload import *
import time

cwd = os.getcwd()

def program_ibmc(bit, bit_path = cwd, console_path = 'd:\\lscc\\diamond\\3.8_x64\\bin\\nt64', usb_port = 'FTUSB-0'):
    '''Save a programming project via diamond programmer as a .xcf file which contains device and bit file information.
    Generate a 'ibmc.tcl' batch file to open and program .xcf file to iBMC.
    Call diamond tcl console to run the batch file.
    After programming succeeds, ibmc.tcl will be removed from the root.'''
    
    #Generate full path for bit file
    bit_file = (bit_path +'\\'+ bit).replace('\\' , '/').replace('//', '/')
    assert_exist(bit_file)
    bit_file_time = time.strftime('%m/%d/%y %H:%M:%S',time.gmtime(os.path.getmtime(bit_file)))
    xcf_file_ = 'ibmc.xcf'
    xcf_file = 'ibmc_temp.xcf'
    
    #Confirm programming operation
    if yesnobox('IBMC', 'iBMC will be programmed to %s. \nProgram?' %(bit)):
        msgbox('IBMC', '- Power board off\n-  Put jumper on J14\n- Connect Lattice programmer on iBMC JTAG\n- Power board back on\n- Click OK to continue')
        
        #Full path for console application
        app = (console_path +'\\'+'pnmainc.exe').replace('\\' , '/').replace('//', '/')
        assert_exist(app)
        assert_exist(xcf_file_)
        
        with open(xcf_file_,'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            lines[i] = lines[i].replace('{bit_file}', bit_file)
            lines[i] = lines[i].replace('{bit_file_time}', bit_file_time)
            lines[i] = lines[i].replace('{usb_port}', usb_port)

        with open(xcf_file,'w') as f:
            f.writelines(lines)

        #Generate a temporary .tcl batch file in root.
        tcl_file = 'ibmc.tcl'
        
        command = [app]
        with open(tcl_file,'w') as f: 
            line = 'pgr_project open ' + xcf_file +'\n'
            f.write(line)
            f.write('pgr_program run\n')
        command.append(tcl_file)   
        command_line = ' '.join(command)  
        
        #Call shell to run diamond tcl console for programming. Catch output and error. 
        try:
            print 'Programming iBMC. This operation may take several minutes.'
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, stderr = p.communicate()
            print output

        except Exception, e:
            return False, output, e.message          

        #Check if no errors caught, return True and output information. Otherwise return False and error info.
        if stderr == '':
            os.remove(xcf_file)
            os.remove(tcl_file)
            msgbox('IBMC', '- Power board off\n- Remove jumper on J14\n- Power board back on\n- Click OK to continue')
            return True, output, command_line
        else:
            return False, output, stderr            
            
    #Return True if manually cancel the programmiing operation.
    else:
        print 'iBMC will not be programmed'
        return True, None        

def program_kintex(mcs, mcs_path = cwd, console_path = 'D:\\Xilinx\\Vivado_Lab\\2016.3\\bin'):
    '''Read the original tcl file from KLIN folder to root. Edit the mcs path line and save to root as 'kintex.tcl'
    Call tcl console 'vivado_lab.bat' to run the batch file.
    After programming succeeds, kintex.tcl will be removed from the root.'''
    
    #Generate full path for mcs and tcl file 
    mcs_file = (mcs_path +'\\'+ mcs).replace('\\' , '/')
    assert_exist(mcs_file)
    tcl_file_ = 'Kintex.tcl'
    assert_exist(tcl_file_)
    
    if yesnobox('KINTEX', 'Kintex will be programmed to %s. \nProgram?' %(mcs)):
        msgbox('KINTEX', '- Power off the board.\n- Put jumper on TxRx\n- Put jumper on J14\n- Connect Xilinx programmer on KTX JTAG\n- Power board back on\n- Verify green "status" LED on Xilinx programmer (power cycle and check connections if amber)\n- Click OK to continue')
        app = console_path +'\\'+'vivado_lab.bat'
        assert_exist(app)
        tcl_file = 'kintex_temp.tcl'
        command = [app, '-mode', 'batch', '-source']
        
        #Read original tcl file
        with open(tcl_file_,'r') as f:
            lines = f.readlines()
        for i, l in enumerate(lines):
            if 'set programming_files' in l:
                lines[i] = 'set programming_files '+ mcs_file +'\n'

        #Save the modified tcl file in root
        with open(tcl_file,'w') as f:
            f.writelines(lines)
        command.append(tcl_file)    
        command_line = ' '.join(command)

        try:
            print 'Programming Kintex. This operation may take a few minutes.'
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
            output = []
            for line in iter(p.stdout.readline, b''):
                if line[0] != '#':
                    print line,
                output.append(line)
            stdout, stderr = p.communicate()
            p.stdout.close()
        except Exception, e:
            return False, output, e.message
            
        #Check if no errors caught, return True and output information. Otherwise return False and error info.
        if stderr == '':
            os.remove(tcl_file)
            msgbox('KINTEX', '- Power off Board\n- Remove jumpers and Xilinx programmer\n- Power back on\n- Click OK to continue')
            return True, output, command_line
        else:
            return False, output, stderr
    
    #Return True if manually cancel the programmiing operation.
    else:
        print 'Kintex will not be programmed'
        return True, None
        
if __name__ == '__main__':
    cwd                 = os.getcwd() 
    global_cfg          = config(cwd +'\\'+ 'GlobalSetting.ini')
    section             = 'iBMC'
    ibmc_console_path   = global_cfg.get_str(section, 'ibmc_console_path')
    ibmc_bit_path       = global_cfg.get_str(section, 'ibmc_bit_path')
    ibmc_bit            = global_cfg.get_str(section, 'ibmc_bit')
    ibmc_usb_port       = global_cfg.get_str(section, 'ibmc_usb_port')
    
    section             = 'Kintex'
    ktx_console_path    = global_cfg.get_str(section, 'ktx_console_path')
    ktx_path_vs         = global_cfg.get_str(section, 'ktx_path_vs')
    ktx_mcs_vs          = global_cfg.get_str(section, 'ktx_mcs_vs')
    ktx_path_ch         = global_cfg.get_str(section, 'ktx_path_ch')
    ktx_mcs_ch          = global_cfg.get_str(section, 'ktx_mcs_ch')
    

    res = program_ibmc(ibmc_bit, ibmc_bit_path, ibmc_console_path, ibmc_usb_port)
    res = program_kintex(ktx_mcs_vs, ktx_path_vs, ktx_console_path)
    res = program_kintex(ktx_mcs_ch, ktx_path_ch, ktx_console_path)