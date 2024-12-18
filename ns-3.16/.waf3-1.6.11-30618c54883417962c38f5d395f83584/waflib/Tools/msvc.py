#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import os,sys,re,tempfile
try:
	import _winreg
except:
	try:
		import winreg as _winreg
	except:
		_winreg=None
from waflib import Utils,TaskGen,Runner,Configure,Task,Options
from waflib.Logs import debug,info,warn,error
from waflib.TaskGen import after_method,before_method,feature
from waflib.Configure import conf
from waflib.Tools import ccroot,c,cxx,ar,winres
g_msvc_systemlibs='''
aclui activeds ad1 adptif adsiid advapi32 asycfilt authz bhsupp bits bufferoverflowu cabinet
cap certadm certidl ciuuid clusapi comctl32 comdlg32 comsupp comsuppd comsuppw comsuppwd comsvcs
credui crypt32 cryptnet cryptui d3d8thk daouuid dbgeng dbghelp dciman32 ddao35 ddao35d
ddao35u ddao35ud delayimp dhcpcsvc dhcpsapi dlcapi dnsapi dsprop dsuiext dtchelp
faultrep fcachdll fci fdi framedyd framedyn gdi32 gdiplus glauxglu32 gpedit gpmuuid
gtrts32w gtrtst32hlink htmlhelp httpapi icm32 icmui imagehlp imm32 iphlpapi iprop
kernel32 ksguid ksproxy ksuser libcmt libcmtd libcpmt libcpmtd loadperf lz32 mapi
mapi32 mgmtapi minidump mmc mobsync mpr mprapi mqoa mqrt msacm32 mscms mscoree
msdasc msimg32 msrating mstask msvcmrt msvcurt msvcurtd mswsock msxml2 mtx mtxdm
netapi32 nmapinmsupp npptools ntdsapi ntdsbcli ntmsapi ntquery odbc32 odbcbcp
odbccp32 oldnames ole32 oleacc oleaut32 oledb oledlgolepro32 opends60 opengl32
osptk parser pdh penter pgobootrun pgort powrprof psapi ptrustm ptrustmd ptrustu
ptrustud qosname rasapi32 rasdlg rassapi resutils riched20 rpcndr rpcns4 rpcrt4 rtm
rtutils runtmchk scarddlg scrnsave scrnsavw secur32 sensapi setupapi sfc shell32
shfolder shlwapi sisbkup snmpapi sporder srclient sti strsafe svcguid tapi32 thunk32
traffic unicows url urlmon user32 userenv usp10 uuid uxtheme vcomp vcompd vdmdbg
version vfw32 wbemuuid  webpost wiaguid wininet winmm winscard winspool winstrm
wintrust wldap32 wmiutils wow32 ws2_32 wsnmp32 wsock32 wst wtsapi32 xaswitch xolehlp
'''.split()
all_msvc_platforms=[('x64','amd64'),('x86','x86'),('ia64','ia64'),('x86_amd64','amd64'),('x86_ia64','ia64')]
all_wince_platforms=[('armv4','arm'),('armv4i','arm'),('mipsii','mips'),('mipsii_fp','mips'),('mipsiv','mips'),('mipsiv_fp','mips'),('sh4','sh'),('x86','cex86')]
all_icl_platforms=[('intel64','amd64'),('em64t','amd64'),('ia32','x86'),('Itanium','ia64')]
def options(opt):
	opt.add_option('--msvc_version',type='string',help='msvc version, eg: "msvc 10.0,msvc 9.0"',default='')
	opt.add_option('--msvc_targets',type='string',help='msvc targets, eg: "x64,arm"',default='')
def setup_msvc(conf,versions):
	platforms=getattr(Options.options,'msvc_targets','').split(',')
	if platforms==['']:
		platforms=Utils.to_list(conf.env['MSVC_TARGETS'])or[i for i,j in all_msvc_platforms+all_icl_platforms+all_wince_platforms]
	desired_versions=getattr(Options.options,'msvc_version','').split(',')
	if desired_versions==['']:
		desired_versions=conf.env['MSVC_VERSIONS']or[v for v,_ in versions][::-1]
	versiondict=dict(versions)
	for version in desired_versions:
		try:
			targets=dict(versiondict[version])
			for target in platforms:
				try:
					arch,(p1,p2,p3)=targets[target]
					compiler,revision=version.rsplit(' ',1)
					return compiler,revision,p1,p2,p3
				except KeyError:continue
		except KeyError:continue
	conf.fatal('msvc: Impossible to find a valid architecture for building (in setup_msvc)')
def get_msvc_version(conf,compiler,version,target,vcvars):
	debug('msvc: get_msvc_version: %r %r %r',compiler,version,target)
	batfile=conf.bldnode.make_node('waf-print-msvc.bat')
	batfile.write("""@echo off
set INCLUDE=
set LIB=
call "%s" %s
echo PATH=%%PATH%%
echo INCLUDE=%%INCLUDE%%
echo LIB=%%LIB%%
"""%(vcvars,target))
	sout=conf.cmd_and_log(['cmd','/E:on','/V:on','/C',batfile.abspath()])
	lines=sout.splitlines()
	if not lines[0]:lines=lines[1:]
	for x in('Setting environment','Setting SDK environment','Intel(R) C++ Compiler','Intel Parallel Studio'):
		if lines[0].find(x)!=-1:
			break
	else:
		debug('msvc: get_msvc_version: %r %r %r -> not found',compiler,version,target)
		conf.fatal('msvc: Impossible to find a valid architecture for building (in get_msvc_version)')
	for line in lines[1:]:
		if line.startswith('PATH='):
			path=line[5:]
			MSVC_PATH=path.split(';')
		elif line.startswith('INCLUDE='):
			MSVC_INCDIR=[i for i in line[8:].split(';')if i]
		elif line.startswith('LIB='):
			MSVC_LIBDIR=[i for i in line[4:].split(';')if i]
	env={}
	env.update(os.environ)
	env.update(PATH=path)
	compiler_name,linker_name,lib_name=_get_prog_names(conf,compiler)
	cxx=conf.find_program(compiler_name,path_list=MSVC_PATH)
	cxx=conf.cmd_to_list(cxx)
	if'CL'in env:
		del(env['CL'])
	try:
		try:
			conf.cmd_and_log(cxx+['/help'],env=env)
		except Exception as e:
			debug('msvc: get_msvc_version: %r %r %r -> failure'%(compiler,version,target))
			debug(str(e))
			conf.fatal('msvc: cannot run the compiler (in get_msvc_version)')
		else:
			debug('msvc: get_msvc_version: %r %r %r -> OK',compiler,version,target)
	finally:
		conf.env[compiler_name]=''
	return(MSVC_PATH,MSVC_INCDIR,MSVC_LIBDIR)
def gather_wsdk_versions(conf,versions):
	version_pattern=re.compile('^v..?.?\...?.?')
	try:
		all_versions=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Microsoft\\Microsoft SDKs\\Windows')
	except WindowsError:
		try:
			all_versions=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Microsoft\\Microsoft SDKs\\Windows')
		except WindowsError:
			return
	index=0
	while 1:
		try:
			version=_winreg.EnumKey(all_versions,index)
		except WindowsError:
			break
		index=index+1
		if not version_pattern.match(version):
			continue
		try:
			msvc_version=_winreg.OpenKey(all_versions,version)
			path,type=_winreg.QueryValueEx(msvc_version,'InstallationFolder')
		except WindowsError:
			continue
		if os.path.isfile(os.path.join(path,'bin','SetEnv.cmd')):
			targets=[]
			for target,arch in all_msvc_platforms:
				try:
					targets.append((target,(arch,conf.get_msvc_version('wsdk',version,'/'+target,os.path.join(path,'bin','SetEnv.cmd')))))
				except conf.errors.ConfigurationError:
					pass
			versions.append(('wsdk '+version[1:],targets))
def gather_wince_supported_platforms():
	supported_wince_platforms=[]
	try:
		ce_sdk=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Microsoft\\Windows CE Tools\\SDKs')
	except WindowsError:
		try:
			ce_sdk=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Microsoft\\Windows CE Tools\\SDKs')
		except WindowsError:
			ce_sdk=''
	if not ce_sdk:
		return supported_wince_platforms
	ce_index=0
	while 1:
		try:
			sdk_device=_winreg.EnumKey(ce_sdk,ce_index)
		except WindowsError:
			break
		ce_index=ce_index+1
		sdk=_winreg.OpenKey(ce_sdk,sdk_device)
		try:
			path,type=_winreg.QueryValueEx(sdk,'SDKRootDir')
		except WindowsError:
			try:
				path,type=_winreg.QueryValueEx(sdk,'SDKInformation')
				path,xml=os.path.split(path)
			except WindowsError:
				continue
		path=str(path)
		path,device=os.path.split(path)
		if not device:
			path,device=os.path.split(path)
		for arch,compiler in all_wince_platforms:
			platforms=[]
			if os.path.isdir(os.path.join(path,device,'Lib',arch)):
				platforms.append((arch,compiler,os.path.join(path,device,'Include',arch),os.path.join(path,device,'Lib',arch)))
			if platforms:
				supported_wince_platforms.append((device,platforms))
	return supported_wince_platforms
def gather_msvc_detected_versions():
	version_pattern=re.compile('^(\d\d?\.\d\d?)(Exp)?$')
	detected_versions=[]
	for vcver,vcvar in[('VCExpress','Exp'),('VisualStudio','')]:
		try:
			prefix='SOFTWARE\\Wow6432node\\Microsoft\\'+vcver
			all_versions=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,prefix)
		except WindowsError:
			try:
				prefix='SOFTWARE\\Microsoft\\'+vcver
				all_versions=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,prefix)
			except WindowsError:
				continue
		index=0
		while 1:
			try:
				version=_winreg.EnumKey(all_versions,index)
			except WindowsError:
				break
			index=index+1
			match=version_pattern.match(version)
			if not match:
				continue
			else:
				versionnumber=float(match.group(1))
			detected_versions.append((versionnumber,version+vcvar,prefix+"\\"+version))
	def fun(tup):
		return tup[0]
	try:
		detected_versions.sort(key=fun)
	except:
		detected_versions.sort(lambda x,y:cmp(x[0],y[0]))
	return detected_versions
def gather_msvc_targets(conf,versions,version,vc_path):
	targets=[]
	if os.path.isfile(os.path.join(vc_path,'vcvarsall.bat')):
		for target,realtarget in all_msvc_platforms[::-1]:
			try:
				targets.append((target,(realtarget,conf.get_msvc_version('msvc',version,target,os.path.join(vc_path,'vcvarsall.bat')))))
			except conf.errors.ConfigurationError:
				pass
	elif os.path.isfile(os.path.join(vc_path,'Common7','Tools','vsvars32.bat')):
		try:
			targets.append(('x86',('x86',conf.get_msvc_version('msvc',version,'x86',os.path.join(vc_path,'Common7','Tools','vsvars32.bat')))))
		except conf.errors.ConfigurationError:
			pass
	elif os.path.isfile(os.path.join(vc_path,'Bin','vcvars32.bat')):
		try:
			targets.append(('x86',('x86',conf.get_msvc_version('msvc',version,'',os.path.join(vc_path,'Bin','vcvars32.bat')))))
		except conf.errors.ConfigurationError:
			pass
	versions.append(('msvc '+version,targets))
def gather_wince_targets(conf,versions,version,vc_path,vsvars,supported_platforms):
	for device,platforms in supported_platforms:
		cetargets=[]
		for platform,compiler,include,lib in platforms:
			winCEpath=os.path.join(vc_path,'ce')
			if not os.path.isdir(winCEpath):
				continue
			try:
				common_bindirs,_1,_2=conf.get_msvc_version('msvc',version,'x86',vsvars)
			except conf.errors.ConfigurationError:
				continue
			if os.path.isdir(os.path.join(winCEpath,'lib',platform)):
				bindirs=[os.path.join(winCEpath,'bin',compiler),os.path.join(winCEpath,'bin','x86_'+compiler)]+common_bindirs
				incdirs=[os.path.join(winCEpath,'include'),os.path.join(winCEpath,'atlmfc','include'),include]
				libdirs=[os.path.join(winCEpath,'lib',platform),os.path.join(winCEpath,'atlmfc','lib',platform),lib]
				cetargets.append((platform,(platform,(bindirs,incdirs,libdirs))))
		if cetargets:
			versions.append((device+' '+version,cetargets))
def gather_msvc_versions(conf,versions):
	vc_paths=[]
	for(v,version,reg)in gather_msvc_detected_versions():
		try:
			try:
				msvc_version=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,reg+"\\Setup\\VC")
			except WindowsError:
				msvc_version=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,reg+"\\Setup\\Microsoft Visual C++")
			path,type=_winreg.QueryValueEx(msvc_version,'ProductDir')
			vc_paths.append((version,os.path.abspath(str(path))))
		except WindowsError:
			continue
	wince_supported_platforms=gather_wince_supported_platforms()
	for version,vc_path in vc_paths:
		vs_path=os.path.dirname(vc_path)
		vsvars=os.path.join(vs_path,'Common7','Tools','vsvars32.bat')
		if wince_supported_platforms and os.path.isfile(vsvars):
			conf.gather_wince_targets(versions,version,vc_path,vsvars,wince_supported_platforms)
	for version,vc_path in vc_paths:
		vs_path=os.path.dirname(vc_path)
		conf.gather_msvc_targets(versions,version,vc_path)
def gather_icl_versions(conf,versions):
	version_pattern=re.compile('^...?.?\....?.?')
	try:
		all_versions=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Wow6432node\\Intel\\Compilers\\C++')
	except WindowsError:
		try:
			all_versions=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,'SOFTWARE\\Intel\\Compilers\\C++')
		except WindowsError:
			return
	index=0
	while 1:
		try:
			version=_winreg.EnumKey(all_versions,index)
		except WindowsError:
			break
		index=index+1
		if not version_pattern.match(version):
			continue
		targets=[]
		for target,arch in all_icl_platforms:
			try:
				if target=='intel64':targetDir='EM64T_NATIVE'
				else:targetDir=target
				_winreg.OpenKey(all_versions,version+'\\'+targetDir)
				icl_version=_winreg.OpenKey(all_versions,version)
				path,type=_winreg.QueryValueEx(icl_version,'ProductDir')
				if os.path.isfile(os.path.join(path,'bin','iclvars.bat')):
					try:
						targets.append((target,(arch,conf.get_msvc_version('intel',version,target,os.path.join(path,'bin','iclvars.bat')))))
					except conf.errors.ConfigurationError:
						pass
			except WindowsError:
				pass
		for target,arch in all_icl_platforms:
			try:
				icl_version=_winreg.OpenKey(all_versions,version+'\\'+target)
				path,type=_winreg.QueryValueEx(icl_version,'ProductDir')
				if os.path.isfile(os.path.join(path,'bin','iclvars.bat')):
					try:
						targets.append((target,(arch,conf.get_msvc_version('intel',version,target,os.path.join(path,'bin','iclvars.bat')))))
					except conf.errors.ConfigurationError:
						pass
			except WindowsError:
				continue
		major=version[0:2]
		versions.append(('intel '+major,targets))
def get_msvc_versions(conf):
	if not conf.env['MSVC_INSTALLED_VERSIONS']:
		lst=[]
		conf.gather_icl_versions(lst)
		conf.gather_wsdk_versions(lst)
		conf.gather_msvc_versions(lst)
		conf.env['MSVC_INSTALLED_VERSIONS']=lst
	return conf.env['MSVC_INSTALLED_VERSIONS']
def print_all_msvc_detected(conf):
	for version,targets in conf.env['MSVC_INSTALLED_VERSIONS']:
		info(version)
		for target,l in targets:
			info("\t"+target)
def detect_msvc(conf):
	versions=get_msvc_versions(conf)
	return setup_msvc(conf,versions)
def find_lt_names_msvc(self,libname,is_static=False):
	lt_names=['lib%s.la'%libname,'%s.la'%libname,]
	for path in self.env['LIBPATH']:
		for la in lt_names:
			laf=os.path.join(path,la)
			dll=None
			if os.path.exists(laf):
				ltdict=Utils.read_la_file(laf)
				lt_libdir=None
				if ltdict.get('libdir',''):
					lt_libdir=ltdict['libdir']
				if not is_static and ltdict.get('library_names',''):
					dllnames=ltdict['library_names'].split()
					dll=dllnames[0].lower()
					dll=re.sub('\.dll$','',dll)
					return(lt_libdir,dll,False)
				elif ltdict.get('old_library',''):
					olib=ltdict['old_library']
					if os.path.exists(os.path.join(path,olib)):
						return(path,olib,True)
					elif lt_libdir!=''and os.path.exists(os.path.join(lt_libdir,olib)):
						return(lt_libdir,olib,True)
					else:
						return(None,olib,True)
				else:
					raise self.errors.WafError('invalid libtool object file: %s'%laf)
	return(None,None,None)
def libname_msvc(self,libname,is_static=False):
	lib=libname.lower()
	lib=re.sub('\.lib$','',lib)
	if lib in g_msvc_systemlibs:
		return lib
	lib=re.sub('^lib','',lib)
	if lib=='m':
		return None
	(lt_path,lt_libname,lt_static)=self.find_lt_names_msvc(lib,is_static)
	if lt_path!=None and lt_libname!=None:
		if lt_static==True:
			return os.path.join(lt_path,lt_libname)
	if lt_path!=None:
		_libpaths=[lt_path]+self.env['LIBPATH']
	else:
		_libpaths=self.env['LIBPATH']
	static_libs=['lib%ss.lib'%lib,'lib%s.lib'%lib,'%ss.lib'%lib,'%s.lib'%lib,]
	dynamic_libs=['lib%s.dll.lib'%lib,'lib%s.dll.a'%lib,'%s.dll.lib'%lib,'%s.dll.a'%lib,'lib%s_d.lib'%lib,'%s_d.lib'%lib,'%s.lib'%lib,]
	libnames=static_libs
	if not is_static:
		libnames=dynamic_libs+static_libs
	for path in _libpaths:
		for libn in libnames:
			if os.path.exists(os.path.join(path,libn)):
				debug('msvc: lib found: %s'%os.path.join(path,libn))
				return re.sub('\.lib$','',libn)
	self.fatal("The library %r could not be found"%libname)
	return re.sub('\.lib$','',libname)
def check_lib_msvc(self,libname,is_static=False,uselib_store=None):
	libn=self.libname_msvc(libname,is_static)
	if not uselib_store:
		uselib_store=libname.upper()
	if False and is_static:
		self.env['STLIB_'+uselib_store]=[libn]
	else:
		self.env['LIB_'+uselib_store]=[libn]
def check_libs_msvc(self,libnames,is_static=False):
	for libname in Utils.to_list(libnames):
		self.check_lib_msvc(libname,is_static)
def configure(conf):
	conf.autodetect()
	conf.find_msvc()
	conf.msvc_common_flags()
	conf.cc_load_tools()
	conf.cxx_load_tools()
	conf.cc_add_flags()
	conf.cxx_add_flags()
	conf.link_add_flags()
	conf.visual_studio_add_flags()
def no_autodetect(conf):
	conf.env.NO_MSVC_DETECT=1
	configure(conf)
def autodetect(conf):
	v=conf.env
	if v.NO_MSVC_DETECT:
		return
	compiler,version,path,includes,libdirs=conf.detect_msvc()
	v['PATH']=path
	v['INCLUDES']=includes
	v['LIBPATH']=libdirs
	v['MSVC_COMPILER']=compiler
	try:
		v['MSVC_VERSION']=float(version)
	except:
		v['MSVC_VERSION']=float(version[:-3])
def _get_prog_names(conf,compiler):
	if compiler=='intel':
		compiler_name='ICL'
		linker_name='XILINK'
		lib_name='XILIB'
	else:
		compiler_name='CL'
		linker_name='LINK'
		lib_name='LIB'
	return compiler_name,linker_name,lib_name
def find_msvc(conf):
	if sys.platform=='cygwin':
		conf.fatal('MSVC module does not work under cygwin Python!')
	v=conf.env
	path=v['PATH']
	compiler=v['MSVC_COMPILER']
	version=v['MSVC_VERSION']
	compiler_name,linker_name,lib_name=_get_prog_names(conf,compiler)
	v.MSVC_MANIFEST=(compiler=='msvc'and version>=8)or(compiler=='wsdk'and version>=6)or(compiler=='intel'and version>=11)
	cxx=None
	if v['CXX']:cxx=v['CXX']
	elif'CXX'in conf.environ:cxx=conf.environ['CXX']
	cxx=conf.find_program(compiler_name,var='CXX',path_list=path)
	cxx=conf.cmd_to_list(cxx)
	env=dict(conf.environ)
	if path:env.update(PATH=';'.join(path))
	if not conf.cmd_and_log(cxx+['/nologo','/help'],env=env):
		conf.fatal('the msvc compiler could not be identified')
	v['CC']=v['CXX']=cxx
	v['CC_NAME']=v['CXX_NAME']='msvc'
	if not v['LINK_CXX']:
		link=conf.find_program(linker_name,path_list=path)
		if link:v['LINK_CXX']=link
		else:conf.fatal('%s was not found (linker)'%linker_name)
		v['LINK']=link
	if not v['LINK_CC']:
		v['LINK_CC']=v['LINK_CXX']
	if not v['AR']:
		stliblink=conf.find_program(lib_name,path_list=path,var='AR')
		if not stliblink:return
		v['ARFLAGS']=['/NOLOGO']
	if v.MSVC_MANIFEST:
		mt=conf.find_program('MT',path_list=path,var='MT')
		v['MTFLAGS']=['/NOLOGO']
	conf.load('winres')
	if not conf.env['WINRC']:
		warn('Resource compiler not found. Compiling resource file is disabled')
def visual_studio_add_flags(self):
	v=self.env
	try:v.prepend_value('INCLUDES',self.environ['INCLUDE'].split(';'))
	except:pass
	try:v.prepend_value('LIBPATH',self.environ['LIB'].split(';'))
	except:pass
def msvc_common_flags(conf):
	v=conf.env
	v['DEST_BINFMT']='pe'
	v.append_value('CFLAGS',['/nologo'])
	v.append_value('CXXFLAGS',['/nologo'])
	v['DEFINES_ST']='/D%s'
	v['CC_SRC_F']=''
	v['CC_TGT_F']=['/c','/Fo']
	if v['MSVC_VERSION']>=8:
		v['CC_TGT_F']=['/FC']+v['CC_TGT_F']
	v['CXX_SRC_F']=''
	v['CXX_TGT_F']=['/c','/Fo']
	if v['MSVC_VERSION']>=8:
		v['CXX_TGT_F']=['/FC']+v['CXX_TGT_F']
	v['CPPPATH_ST']='/I%s'
	v['AR_TGT_F']=v['CCLNK_TGT_F']=v['CXXLNK_TGT_F']='/OUT:'
	v['CFLAGS_CONSOLE']=v['CXXFLAGS_CONSOLE']=['/SUBSYSTEM:CONSOLE']
	v['CFLAGS_NATIVE']=v['CXXFLAGS_NATIVE']=['/SUBSYSTEM:NATIVE']
	v['CFLAGS_POSIX']=v['CXXFLAGS_POSIX']=['/SUBSYSTEM:POSIX']
	v['CFLAGS_WINDOWS']=v['CXXFLAGS_WINDOWS']=['/SUBSYSTEM:WINDOWS']
	v['CFLAGS_WINDOWSCE']=v['CXXFLAGS_WINDOWSCE']=['/SUBSYSTEM:WINDOWSCE']
	v['CFLAGS_CRT_MULTITHREADED']=v['CXXFLAGS_CRT_MULTITHREADED']=['/MT']
	v['CFLAGS_CRT_MULTITHREADED_DLL']=v['CXXFLAGS_CRT_MULTITHREADED_DLL']=['/MD']
	v['CFLAGS_CRT_MULTITHREADED_DBG']=v['CXXFLAGS_CRT_MULTITHREADED_DBG']=['/MTd']
	v['CFLAGS_CRT_MULTITHREADED_DLL_DBG']=v['CXXFLAGS_CRT_MULTITHREADED_DLL_DBG']=['/MDd']
	v['LIB_ST']='%s.lib'
	v['LIBPATH_ST']='/LIBPATH:%s'
	v['STLIB_ST']='lib%s.lib'
	v['STLIBPATH_ST']='/LIBPATH:%s'
	v.append_value('LINKFLAGS',['/NOLOGO'])
	if v['MSVC_MANIFEST']:
		v.append_value('LINKFLAGS',['/MANIFEST'])
	v['CFLAGS_cshlib']=[]
	v['CXXFLAGS_cxxshlib']=[]
	v['LINKFLAGS_cshlib']=v['LINKFLAGS_cxxshlib']=['/DLL']
	v['cshlib_PATTERN']=v['cxxshlib_PATTERN']='%s.dll'
	v['implib_PATTERN']='%s.lib'
	v['IMPLIB_ST']='/IMPLIB:%s'
	v['LINKFLAGS_cstlib']=[]
	v['cstlib_PATTERN']=v['cxxstlib_PATTERN']='lib%s.lib'
	v['cprogram_PATTERN']=v['cxxprogram_PATTERN']='%s.exe'
def apply_flags_msvc(self):
	if self.env.CC_NAME!='msvc'or not getattr(self,'link_task',None):
		return
	is_static=isinstance(self.link_task,ccroot.stlink_task)
	subsystem=getattr(self,'subsystem','')
	if subsystem:
		subsystem='/subsystem:%s'%subsystem
		flags=is_static and'ARFLAGS'or'LINKFLAGS'
		self.env.append_value(flags,subsystem)
	if not is_static:
		for f in self.env.LINKFLAGS:
			d=f.lower()
			if d[1:]=='debug':
				pdbnode=self.link_task.outputs[0].change_ext('.pdb')
				self.link_task.outputs.append(pdbnode)
				try:
					self.install_task.source.append(pdbnode)
				except AttributeError:
					pass
				break
def apply_manifest(self):
	if self.env.CC_NAME=='msvc'and self.env.MSVC_MANIFEST and getattr(self,'link_task',None):
		out_node=self.link_task.outputs[0]
		man_node=out_node.parent.find_or_declare(out_node.name+'.manifest')
		self.link_task.outputs.append(man_node)
		self.link_task.do_manifest=True
def exec_mf(self):
	env=self.env
	mtool=env['MT']
	if not mtool:
		return 0
	self.do_manifest=False
	outfile=self.outputs[0].abspath()
	manifest=None
	for out_node in self.outputs:
		if out_node.name.endswith('.manifest'):
			manifest=out_node.abspath()
			break
	if manifest is None:
		return 0
	mode=''
	if'cprogram'in self.generator.features or'cxxprogram'in self.generator.features:
		mode='1'
	elif'cshlib'in self.generator.features or'cxxshlib'in self.generator.features:
		mode='2'
	debug('msvc: embedding manifest in mode %r'%mode)
	lst=[]
	lst.append(env['MT'])
	lst.extend(Utils.to_list(env['MTFLAGS']))
	lst.extend(['-manifest',manifest])
	lst.append('-outputresource:%s;%s'%(outfile,mode))
	lst=[lst]
	return self.exec_command(*lst)
def quote_response_command(self,flag):
	if flag.find(' ')>-1:
		for x in('/LIBPATH:','/IMPLIB:','/OUT:','/I'):
			if flag.startswith(x):
				flag='%s"%s"'%(x,flag[len(x):])
				break
		else:
			flag='"%s"'%flag
	return flag
def exec_response_command(self,cmd,**kw):
	try:
		tmp=None
		if sys.platform.startswith('win')and isinstance(cmd,list)and len(' '.join(cmd))>=8192:
			program=cmd[0]
			cmd=[self.quote_response_command(x)for x in cmd]
			(fd,tmp)=tempfile.mkstemp()
			os.write(fd,'\r\n'.join(i.replace('\\','\\\\')for i in cmd[1:]).encode())
			os.close(fd)
			cmd=[program,'@'+tmp]
		ret=self.generator.bld.exec_command(cmd,**kw)
	finally:
		if tmp:
			try:
				os.remove(tmp)
			except:
				pass
	return ret
def exec_command_msvc(self,*k,**kw):
	if self.env['CC_NAME']=='msvc':
		if isinstance(k[0],list):
			lst=[]
			carry=''
			for a in k[0]:
				if a=='/Fo'or a=='/doc'or a[-1]==':':
					carry=a
				else:
					lst.append(carry+a)
					carry=''
			k=[lst]
		if self.env['PATH']:
			env=dict(os.environ)
			env.update(PATH=';'.join(self.env['PATH']))
			kw['env']=env
	bld=self.generator.bld
	try:
		if not kw.get('cwd',None):
			kw['cwd']=bld.cwd
	except AttributeError:
		bld.cwd=kw['cwd']=bld.variant_dir
	ret=self.exec_response_command(k[0],**kw)
	if not ret and getattr(self,'do_manifest',None):
		ret=self.exec_mf()
	return ret
for k in'c cxx cprogram cxxprogram cshlib cxxshlib cstlib cxxstlib'.split():
	cls=Task.classes.get(k,None)
	if cls:
		cls.exec_command=exec_command_msvc
		cls.exec_response_command=exec_response_command
		cls.quote_response_command=quote_response_command
		cls.exec_mf=exec_mf

conf(get_msvc_version)
conf(gather_wsdk_versions)
conf(gather_msvc_targets)
conf(gather_wince_targets)
conf(gather_msvc_versions)
conf(gather_icl_versions)
conf(get_msvc_versions)
conf(print_all_msvc_detected)
conf(detect_msvc)
conf(find_lt_names_msvc)
conf(libname_msvc)
conf(check_lib_msvc)
conf(check_libs_msvc)
conf(no_autodetect)
conf(autodetect)
conf(find_msvc)
conf(visual_studio_add_flags)
conf(msvc_common_flags)
after_method('apply_link')(apply_flags_msvc)
feature('c','cxx')(apply_flags_msvc)
feature('cprogram','cshlib','cxxprogram','cxxshlib')(apply_manifest)
after_method('apply_link')(apply_manifest)