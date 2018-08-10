#!/usr/bin/env python


import argparse,os,logging,re,sys

class Status:
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3

def human_size(bytes, units=[' bytes','KB','MB','GB','TB']):
	return str(bytes) + units[0] if bytes < 1024 else human_size(bytes>>10, units[1:])

def get_device(path):
	with open('/proc/mounts','r') as mounts:
		for line in mounts:
			if not ' ' in line:
				continue
			(device,mountpoint)=line.split()[:2]
			if mountpoint==path and device!='none':
				return device
	return None

def check(path,args,checked_devices,uniquefs):
	if '=' in path:
		(path,alias)=path.split('=',2)
	else:
		alias=None
	optional=False
	if path.endswith('?'):
		path=path[:-1]
		optional=True
	if not os.path.ismount(path):
		if optional:
			logging.debug("Volume %s is not mounted but it's optional - ignoring",path)
			return None # silently ignore
		logging.warn("Volume %s is not mounted",path)
		return {
			'status': Status.CRITICAL,
			'message': '%s is not mounted'%path
		}
	path=os.path.normpath(path)
	if alias is None:
		alias=path
	device=get_device(path)
	if device is not None:
		already_reported=device in checked_devices
		checked_devices.append(device)
		if already_reported:
			logging.debug("Volume %s is on an already reported device",path)
			if uniquefs:
				return None

	stats=os.statvfs(path)

	# https://stackoverflow.com/a/21834323
	bytes_total_unprivileged=stats.f_bsize*(stats.f_blocks-stats.f_bfree+stats.f_bavail)
	bytes_total=stats.f_bsize*stats.f_blocks
	bytes_free=stats.f_bsize*stats.f_bavail
	bytes_used=bytes_total_unprivileged-bytes_free
	bytes_warning=calc_treshold(args,'warn',bytes_total)
	logging.info("Warning treshold for %s is %s (%s)",path,human_size(bytes_warning[0]),bytes_warning[1])
	bytes_critical=calc_treshold(args,'crit',bytes_total)
	logging.info("Critical treshold for %s is %s (%s)",path,human_size(bytes_critical[0]),bytes_critical[1])

	if bytes_free<bytes_critical[0]:
		status=Status.CRITICAL
		message="%s %s (<%s, CRIT)"%(alias,human_size(bytes_free),human_size(bytes_critical[0]))
	elif bytes_free<bytes_warning[0]:
		status=Status.WARNING
		message="%s %s (<%s, WARN)"%(alias,human_size(bytes_free),human_size(bytes_warning[0]))
	else:
		status=Status.OK
		message="%s %s (>=%s, OK)"%(alias,human_size(bytes_free),human_size(bytes_warning[0]))

	return {
		'status': status,
		'message': message,
		'stats': '%s=%sMB;%s;%s;0;%s' % (alias,bytes_used/1024/1024,
			(bytes_total-bytes_warning[0])/1024/1024,
			(bytes_total-bytes_critical[0])/1024/1024,
			bytes_total/1024/1024
			)
	}

def calc_treshold(args,type,bytes_total):

	bytes_treshold_min=None
	bytes_treshold_min_text=None

	for (amount,unit) in getattr(args,type):
		bytes_treshold=calc_treshold_bytes(amount,unit,bytes_total);
		if bytes_treshold_min is None or bytes_treshold_min>bytes_treshold:
			bytes_treshold_min=bytes_treshold
			bytes_treshold_min_text='%s%s'%(amount,unit)
	return [bytes_treshold_min,bytes_treshold_min_text]

def calc_treshold_bytes(amount,unit,bytes_total):
	if unit=='M':
		return int(amount*1024*1024)
	if unit=='G':
		return int(amount*1024*1024*1024)
	if unit=='T':
		return int(amount*1024*1024*1024*1024)
	if unit=='%':
		return int(bytes_total/100*amount)

def threshold_type(s):
	pat=re.compile(r"^(\d+(?:\.\d+)?)([%MGT])(?:,(\d+(?:\.\d+)?)([%MGT]))?$")
	match=pat.match(s)
	if match is None:
		print ("Invalid treshold: %s"%s)
		sys.exit(Status.CRITICAL)
	tresholds=[[float(match.group(1)),match.group(2)]]
	if match.group(3) is not None:
		tresholds.append([float(match.group(3)),match.group(4)])
	return tresholds

def main():
	parser = argparse.ArgumentParser(description='Check free disk space')
	parser.add_argument('--debug','-d',action='store_true')
	parser.add_argument('--uniquefs','-u',action='store_true', help="If two or more checked mounts point to the same device, only the first match will be reported. Ignored if device is 'none'.")
	parser.add_argument('--path','-p',metavar='path',default=['/'],nargs='+', help="A list of paths to check. Append '?' to optional paths. Append '=alias' to set an alias name (e.g. /mnt/data?=/data results in an optional check on /mnt/data which is shown as /data if an alert occurs)")
	parser.add_argument('--warn','-w',default='20%',type=threshold_type,
		help='Min free treshold for warning. Default is 20%%. Examples: "5G","100M", "2T", "1.5%%,25G" (this will use the smaller of both, depending on disk size)')
	parser.add_argument('--crit','-c',default='10%',type=threshold_type,
		help='Min free treshold for critical. Default is 10%%.')
	args = parser.parse_args()

	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG if args.debug else logging.ERROR)

	checked_devices=[]
	status=None
	messages=[]
	stats=[]
	for path in args.path:
		check_result=check(path,args,checked_devices,args.uniquefs)
		if check_result is None:
			continue
		if status is None or status<check_result['status']:
			status=check_result['status']
		messages.append(check_result['message'])
		if 'stats' in check_result:
			stats.append(check_result['stats'])
	if status==Status.OK:
		status_txt='OK'
	elif status==Status.WARNING:
		status_txt='WARNING'
	if status==Status.CRITICAL:
		status_txt='CRITICAL'
	print ('DISK %s - %s|%s' % (status_txt,'; '.join(messages),' '.join(stats)))
	sys.exit(status)

if __name__ == "__main__":
	main()
