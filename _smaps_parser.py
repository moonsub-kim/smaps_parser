import operator, sys
from subprocess import check_output
from subprocess import CalledProcessError
from time import sleep
import argparse

attr_names=["Size", "KernelPageSize",
	"MMUPageSize", "Rss", "Pss",
	"Shared_clean", "Shared_Dirty",
	"Private_clean", "Private_Dirty",
	"Referenced", "Anonymous",
	"LazyFree", "AnonHugePages",
	"ShmemPmdMapped", "Shared_Hugetlb",
	"Private_Hugetlb", "Swap", "SwapPss",
	"Locked"]#, "VmFlags" ]
attr_names = map(lambda x:x.lower(), attr_names)

class smap:
	def __init__(self, line, pid):
		self.read_smap_entry(line, pid)

	def read_smap_entry(self, entry_line, pid):
		# read first line
		meta = entry_line[0].split(" ")
		addr = meta[0].split("-")
		self.addr_start = addr[0]
		self.addr_end = addr[1]
		self.permission = meta[1]
		self.mmap_offset = meta[2]
		self.maj_min = meta[3]
		self.inode = meta[4]
		self.name = _getname(meta)
		self.pid = pid
		# read each line
		data_line = entry_line[1:]
		self.data = {}

		#unit
#		unit_to_value = {
#			'k':1000,
#			'm':1000000,
#			'g':1000000000
#		}

		for i in range(len(data_line)-1):
			line = data_line[i].split(" ")
			size, unit = line[len(line)-2:]
			unit = unit[0]
			self.data[attr_names[i]] = int(size)
#			self.data[attr_names[i]] = int(size)*unit_to_value[unit[0]]

		# vmFlags
		self.data["VmFlags"] = data_line[len(data_line)-1].split(" ")[1:-1]
	
	def printall(self):
		print self.addr_start+"-"+self.addr_end+" "+\
			self.permission+" "+self.mmap_offset+" "+\
			self.maj_min+" "+self.inode+" "+self.name
		print self.data

def _getname(meta):
	name = meta[len(meta)-1].split("\n")[0]
	if(meta[len(meta)-2] != " "):
		name = (meta[len(meta)-2] + " " + name).strip()
	if(len(name) == 0):
		name = "Anonymous"
	return name
		
class smapManager:
	def __init__(self, entire_line, pid, parse_with_shared_object):
		num_entry = len(entire_line) / 21
		self.area = {}
		for i in range(0, num_entry):
			i_start = i * 21
			i_end = (i + 1) * 21

			if parse_with_shared_object == False \
				and (entire_line[i_start].find(".so\n") != -1 \
				or entire_line[i_start].find(".so.") != -1):
				continue
			region_entry = smap(entire_line[i_start:i_end], pid)
			if((region_entry.name in self.area) == False):
				self.area[region_entry.name] = {
					"entries" : [region_entry],
				}
			else:
			 	self.area[region_entry.name]["entries"].append(region_entry)
		self.sum_attr_size()
#		for k in self.area:
#			for a in attr_names:
#				if(a == "VmFlags"):
#					continue
#				self.area[k][a] =  \
#					self.sum_attr_size(self.area[k]["entries"], a)

	def add(self, entire_line, pid, parse_with_shared_object):
		num_entry = len(entire_line) /21
		for i in range(0, num_entry):
			i_start = i * 21
			i_end = (i + 1) *21
			if parse_with_shared_object == False \
				and (entire_line[i_start].find(".so\n") != -1 \
				or entire_line[i_start].find(".so.") != -1):
				continue
			meta = entire_line[i_start].split(" ")
			region_entry = smap(entire_line[i_start:i_end], pid)

			if (region_entry.name in self.area) == True:
			 	self.area[region_entry.name]["entries"].append(region_entry)
			else:
				self.area[region_entry.anme] = {
					"entries" : [region_entry],
				}
		self.sum_attr_size()

	def sum_attr_size(self):
		for k in self.area:
			for a in attr_names:
				if(a == "VmFlags"):
					continue
				sum = 0
				for entry in self.area[k]["entries"]:
					sum = sum + entry.data[a]
				self.area[k][a] = sum
	
	def print_attr_in_area(self, attr_names, pid, thresh):
		for name in attr_names:
			print_str = ""
			is_print = False
			attr_sum = 0
			for k in self.area:
				#print over 1MB
				if(self.area[k][name] > thresh):
					if(is_print == False):
						is_print = True
#print_str += pid + "\n"
						print_str += name + "\n"
					print_str += k + ": " + str(self.area[k][name]) + " kB\n"
				attr_sum += self.area[k][name]
			if(is_print == True):
				print print_str + "\ntotal: " + str(attr_sum) + "kB\n"

def get_entire_line(pid):
	path = "/proc/"+pid+"/smaps"
	try:
		f = open(path, "r")
		entire_line = f.readlines()
		f.close()
	except IOError:
		exit()
	return entire_line


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("process_name", type=str,
			help="process name")
	parser.add_argument("-a", type=str.lower, default="all",
			choices=attr_names, nargs="+",
			help="attributes to print ( default:all )")
	parser.add_argument("-s", action='store_true',
			help="print with shared object")
	parser.add_argument("-p", action='store_true',
			help="print information each pid if process name is matched with N pids")
	parser.add_argument("-v", action='store_true',
			help="verbose")
	parser.add_argument("-t", type=int, default=1000,
			help="threshold of size to print")
	parser.add_argument("-f", type=str, nargs="+",
			help="file to print")
	args = parser.parse_args()
	if args.a == "all":
		args.a = attr_names
	if args.v == True:
		print "arguments :: "
		print "\tthreshold: " + str(args.t)
		print "\tprocess name: " + args.process_name
		print "\tfiles to print: " + str(args.f)
		print "\tattributes: " + str(args.a)
		print ""
	print "Wait for process to run"
	while True:
		#test
		pids=["1"]
		break
		try:
			pids = check_output(["pidof", args.process_name])[:-1].split(" ")
			break
		except CalledProcessError as e:
			continue
	print "Start smaps parser"
	while True:
		entire_line = get_entire_line(pids[0])
		mgr = smapManager(entire_line, pids[0], args.s)
#		for pid in pids[1:]:
#			entire_line = get_entire_line(pid)	
#			mgr.add(entire_line, pid, args.s)
		mgr.print_attr_in_area(args.a, pids, args.t)

		break
		sleep(1)

if __name__ == "__main__":
	main()

