# -*- coding: utf-8 -*-

'''
Created on Thu Sep 29 14:35:48 2016

@author: Yaoyao Zhang
''' 
import logging
import datetime
import h5py 
import Tkinter as tk
import tkMessageBox   
import os
import shutil
import json
from ConfigParser import ConfigParser
import winsound

class config(object):
    def __init__(self, fname):
        self.obj = ConfigParser()
        self.fname = fname
        self.obj.read(fname)
        
    def get_list(self, section, option):
        raw = self.obj.get(section, option)
        l = json.loads(raw)
        return l
        
    def get_int(self, section, option):
        raw = self.obj.getint(section, option)
        return int(raw)
    
    def get_float(self, section, option):
        raw = self.obj.getfloat(section, option)
        return float(raw)
        
    def get_bool(self, section, option):
        raw = self.obj.getboolean(section, option)
        return bool(raw)
        
    def get_str(self, section, option):
        raw = self.obj.get(section, option)
        return str(raw)
    
    def get_items(self, section):
        raw_items = self.obj.items(section)
        items = {}
        for item in raw_items:
            (key, value) = item
            key = str(key)
            try:
                value = json.loads(value)
            except:
                pass
            items[key] = value
        return items
    
    def set_option(self, section, option, value):
        cfgfile = open(self.fname,'w')        
        try:
            if not self.obj.has_section(section):
                self.obj.add_section(section)
            self.obj.set(section, option, value)
            self.obj.write(cfgfile)
            cfgfile.close()
            return True
        except Exception, e:
            cfgfile.close()
            return e.message

def assert_exist(path):
    ver = os.path.exists(path)
    assert ver, '%s doesn''t exist' %(path)

def gen_TestReport(sn, res_path):    
    testnames = ['OUTCOME', 'MONITORS', 'NOISE_FLOOR', 'NOISE_SPECTRUM', 'STATIC_GAIN', 'TIME_GAIN', 'TRANSMIT_FEATURE_ANALOG', 'TRANSMIT_FEATURE_BEAMFORMING'] 
    report_file = res_path + '\\' + sn + '_TestReport.txt'
    with open(report_file, 'w') as f:
        for testname in testnames:
            result_file = res_path + '\\' + sn +'\\'+ sn + '_' + testname + '.txt'
            lines = get_lines(result_file)
            f.writelines(lines)

def get_lines(fname):
    try:
        with open(fname, 'r') as f:
            lines = f.readlines()
        lines.append('\n\n')
        return lines
    except Exception, e:
        print e.message
        print 'Read %s Failed' %(fname)
        return ['Read %s Failed\n\n' %(fname)]
        

        
def verify_version_info(cfg, operation, release_version):
    '''Load gitinfo from current reop. 
    Check if there is saved info in cfg file. If so, compare with the current repo. Ask either overwrite, or cancel the test.
    If no existing gitinfo, or overwrite is confirmed, save the current gitinfo into cfg file.
    '''
    if operation == 'Process':
        return (True, 'Ignore GitInfo verification in ''Process'' operation.')

    #Load git info and verify
    section        = operation + 'Version'
    git_options     = cfg.get_items(section)
    #No existing GitInfo in CFG file
    if git_options  == {}:   
        cfg.set_option(section, 'ReleaseVersion', release_version)
        return (True, 'Version Info saved to cfg file')
    else:    
        #CFG file already contains saved GitInfo
        release_version_cfg   = cfg.get_str(section, 'ReleaseVersion')
        if release_version_cfg != release_version:
            if yesnobox('WARNING', 'Current script version doesn''t match saved version in %s. Overwrite and Continue?' %(cfg.fname)):
                cfg.set_option(section, 'ReleaseVersion', release_version)
                return (True, 'Version Info saved to cfg file')
            else:
                return (False, 'Cancel test. Version Info doesn''t match.')
        else:
            return (True, 'Version Info matched.')

def verify_git_info(cfg, operation):
    '''Load gitinfo from current reop. 
    Check if there is saved info in cfg file. If so, compare with the current repo. Ask either overwrite, or cancel the test.
    If no existing gitinfo, or overwrite is confirmed, save the current gitinfo into cfg file.
    '''
    if operation == 'Process':
        return (True, 'Ignore GitInfo verification in ''Process'' operation.')
    gitinfo = get_git_repo_version('.')
    if gitinfo[0]:
        if gitinfo[-1]:
            if not yesnobox('WARNING', 'Current repo contains uncommitted local changes. Continue?'):
                return (False, 'Cancel test. Uncommitted local changes.')
        (hexsha, tag, branch, author, date, description, dirty) = gitinfo[1:]
    else:
        (hexsha, tag, branch, author, date, description, dirty) = ['']*7

    #Load git info and verify
    section        = operation + 'GitInfo'
    git_options     = cfg.get_items(section)
    #No existing GitInfo in CFG file
    if git_options  == {}:     
        cfg.set_option(section, 'hexsha', hexsha)
        cfg.set_option(section, 'tag', tag)
        cfg.set_option(section, 'branch', branch)
        cfg.set_option(section, 'author', author)
        cfg.set_option(section, 'date', date)
        cfg.set_option(section, 'description', description)
        cfg.set_option(section, 'dirty', dirty)
        return (True, 'GitInfo saved to cfg file')
    else:    
        #CFG file already contains saved GitInfo
        hexsha_cfg   = cfg.get_str(section, 'hexsha')
        if hexsha_cfg != hexsha:
            if yesnobox('WARNING', 'Current repo doesn''t match saved GitInfo in %s. Overwrite and Continue?' %(cfg.fname)):
                cfg.set_option(section, 'hexsha', hexsha)
                cfg.set_option(section, 'tag', tag)
                cfg.set_option(section, 'branch', branch)
                cfg.set_option(section, 'author', author)
                cfg.set_option(section, 'date', date)
                cfg.set_option(section, 'description', description)                
                cfg.set_option(section, 'dirty', dirty)
                return (True, 'GitInfo saved to cfg file')
            else:
                return (False, 'Cancel test. Current repo doesn''t match saved GitInfo.')
        else:
            return (True, 'Current repo matches saved GitInfo.')
                
def init_datapath_cfg(datapath, cfgfile, cfgfile_original):
    try:
        os.makedirs(datapath)
    except Exception, e:
        if e.errno == 17:  #Path already exists
            pass                                
        else:
            print 'Unknown Error!'
            return (False, e)
            
    if os.path.isfile(cfgfile):                
        if yesnobox('OVERWRITE', 'CFG file exists. Yes - Overwrite with new CFG file. No - Load existing CFG file'):
            try:
                shutil.copy(cfgfile_original, cfgfile)
            except Exception, e:
                print 'Unknown Error!'
                return (False, e)  
    else:
        try:
            shutil.copy(cfgfile_original, cfgfile)
        except Exception:
            print 'Unknown Error!'
            return (False, e) 
            
    cfg = config(cfgfile)
    return (True, cfg)    
    
def load_cfg(cfgfile):            
    if not os.path.isfile(cfgfile):              
        return (False, 'CFG file does not exist')
    else:       
        cfg = config(cfgfile)
        return (True, cfg) 
       
def dumpdata(var_list, d, path):  
    '''Dump data as HDF5 binary data format. 
    [Var_list] must match all the variables being dumped.
    Data can be list or ndarrays. Dict is not supported.
    '''
    f = h5py.File(path, 'w')
    for i, var in enumerate(var_list):
        f.create_dataset(var, data = d[i])
    f.close()
    return
    
def loaddata(fname, keys):
    '''Load HDF5 binary data format data. 
    '''
    data = []  
    try:
        f = h5py.File(fname, 'r')
    except IOError:
        print 'h5 file doesn''t exist'
        return data

    try:
        var_list = f['var_list'][:]
    except:
        print 'Load ''var_list'' failed. Data file might be damaged'
        return data
      
    for key in keys:
        if key in var_list:
            data.append(f[key][:])
        else:
            print 'Error: var %s required does not exist' %(key)
    f.close()
    return data

def msgbox(title, msg):
    '''Show a confirmation window with title and msg.
    '''
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)   
    tkMessageBox.showinfo(title=title,message=msg,parent = root)
    return

def yesnobox(title, msg):
    '''Show a confirmation window with title and msg to ask yes or no.
    '''    
    root = tk.Tk()    
    root.withdraw()
    root.attributes("-topmost", True) 
    winsound.MessageBeep()
    res = tkMessageBox.askyesno(title = title,message = msg,parent = root)
    return res
    
def set_logger(savepath, logpath, serial, testname, release_version):
    '''Initialize two log files and handlers: 'CRITICAL' to record test results and 'INFO' to record all the log info.
    Time and versions are recorded in the beginning of the log files.
    '''
    log = logging.getLogger('log')
    log.setLevel(logging.INFO)
    log_file = logpath+serial+'_'+testname+'.log'
    result_file = savepath+serial+'_'+testname+'.txt'

    try:
        os.makedirs(logpath)
    except OSError:
        #If files already exist, clear the files' old contents by opening the files.
        with open(log_file,'w'): pass
        with open(result_file,'w'): pass   
    except:
        #Raise other errors
        raise

    log.handlers = []
    
    fmt1 = logging.Formatter('%(message)s')
    hdr1 = logging.FileHandler(log_file)
    hdr1.setFormatter(fmt1)
    hdr1.setLevel(logging.INFO)
    log.addHandler(hdr1)
    
    fmt2 = logging.Formatter('%(message)s')
    hdr2 = logging.FileHandler(result_file)
    hdr2.setFormatter(fmt2)
    hdr2.setLevel(logging.CRITICAL)
    log.addHandler(hdr2)
    
    #Print test time to log files
    t = datetime.datetime.now()
    log.critical(serial+'\t'+testname)
    log.critical(t.strftime('%d/%m/%Y\t')+t.strftime('%H:%M'))
    log.critical('Test Script Release Version: %s\n'%(release_version))            
    return hdr1, hdr2, log

def set_logger_general(savepath, logpath, serial, testname, release_version,logname):
    '''Initialize two log files and handlers: 'CRITICAL' to record test results and 'INFO' to record all the log info.
    Time and versions are recorded in the beginning of the log files.
    '''
    log = logging.getLogger(logname)
    log.setLevel(logging.INFO)
    log_file = logpath+serial+'_'+testname+'_'+logname+'.log'
    result_file = savepath+serial+'_'+testname+'_'+logname+'.txt'

    try:
        os.makedirs(logpath)
    except OSError:
        #If files already exist, clear the files' old contents by opening the files.
        with open(log_file,'w'): pass
        with open(result_file,'w'): pass   
    except:
        #Raise other errors
        raise

    log.handlers = []
    
    fmt1 = logging.Formatter('%(message)s')
    hdr1 = logging.FileHandler(log_file)
    hdr1.setFormatter(fmt1)
    hdr1.setLevel(logging.INFO)
    log.addHandler(hdr1)
    
    fmt2 = logging.Formatter('%(message)s')
    hdr2 = logging.FileHandler(result_file)
    hdr2.setFormatter(fmt2)
    hdr2.setLevel(logging.CRITICAL)
    log.addHandler(hdr2)
    
    #Print test time to log files
    t = datetime.datetime.now()
    log.critical(serial+'\t'+testname)
    log.critical(t.strftime('%d/%m/%Y\t')+t.strftime('%H:%M'))
    log.critical('Test Script Release Version: %s\n'%(release_version))            
    return hdr1, hdr2, log

def get_git_repo_version(repo_path='.'):
    '''Get the test scripts version from github
    '''
    import git
    try:
        repo = git.Repo(repo_path)
    except git.exc.NoSuchPathError:
        # There is no such path.
        return (False, 'WARNING: There is no such path.')
    except git.exc.InvalidGitRepositoryError:
        # There is no Git repo in this path.
        return (False, 'WARNING: There is no Git repo in this path.')

    head = repo.head
    try:
        commit = head.commit
    except ValueError:
        return(False, 'WARNING: No history.')
    else:
        # Find the head's tag, if any.
        tag         = '%s'%next((tag for tag in repo.tags if tag.commit == commit), '')
        hexsha      = '%s'%commit.hexsha
        branch      = '%s'%head.ref
        author      = '%s'%commit.committer
        date        = '%s'%commit.authored_datetime
        description = '%s'%commit.summary
        dirty       = repo.is_dirty()
        
    return (True, hexsha, tag, branch, author, date, description, dirty)
    
def SN_Entry():
    sn = raw_input("Enter Board Serial Number: ")
    return sn
    