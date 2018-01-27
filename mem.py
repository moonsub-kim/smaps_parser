import operator, sys
from subprocess import check_output
from subprocess import CalledProcessError
from time import sleep

attr_names=["Size", "KernelPageSize",
	"MMUPageSize", "Rss", "Pss",
	"Shared_clean", "Shared_Dirty",
	"Private_clean", "Private_Dirty",
	"Referenced", "Anonymous",
	"LazyFree", "AnonHugePages",
	"ShmemPmdMapped", "Shared_Hugetlb",
	"Private_Hugetlb", "Swap", "SwapPss",
	"Locked"]#, "VmFlags" ]

class smap:
	def __init__(self, line):
		self.read_smap_entry(line)

	def read_smap_entry(self, entry_line):
		# read first line
		meta = entry_line[0].split(" ")
		addr = meta[0].split("-")
		self.addr_start = addr[0]
		self.addr_end = addr[1]
		self.permission = meta[1]
		self.mmap_offset = meta[2]
		self.maj_min = meta[3]
		self.inode = meta[4]
		self.name = meta[len(meta)-1].split("\n")[0]
		if(meta[len(meta)-2] != " "):
			self.name = meta[len(meta)-2] + " " + self.name
		if(len(self.name) == 0):
			self.name = "Anonymous"
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

class smapManager:
	def __init__(self, entire_line):
		num_entry = len(entire_line) / 21
		self.region = []
		self.area = {}
		for i in range(0, num_entry):
			i_start = i * 21
			i_end = (i + 1) * 21
			region_entry = smap(entire_line[i_start:i_end])
			self.region.append(region_entry)
			if((region_entry.name in self.area) == False):
				self.area[region_entry.name] = {
					"entries" : [region_entry],
				}
			else:
			 	self.area[region_entry.name]["entries"].append(region_entry)
		for k in self.area:
			for a in attr_names:
				if(a == "VmFlags"):
					continue
				self.area[k][a] =  \
					self.sum_attr_size(self.area[k]["entries"], a)

	def sum_attr_size(self, entries, attr_name):
		sum = 0
		for entry in entries:
			sum = sum + entry.data[attr_name]
		return sum
	
	def print_attr_in_area(self, attr_names, pid):
		for name in attr_names:
			print_str = ""
			is_print = False
			for k in self.area:
				#print over 1MB
				if(self.area[k][name] > 10000):
					if(is_print == False):
						is_print = True
						print_str += pid + "\n"
						print_str += name + "\n"
					print_str += k + ": " + str(self.area[k][name]) + " kB\n"
			if(is_print == True):
				print print_str + "\n"


if(len(sys.argv) != 3):
	print "Usage: python " + sys.argv[0] + " {process_name} {attr}"
	print "attr :: " + str(attr_names)
	exit()


process_name = sys.argv[1]
attr = sys.argv[2].split(",")
if(attr[0] == "all"):
	attr = attr_names

print "Wait for process to run"
while True:
	try:
		pids = check_output(["pidof", process_name])[:-1].split(" ")
		break
	except CalledProcessError as e:
		continue
print "Start smaps parser"
while True:
	for pid in pids:
		path = "/proc/"+pid+"/smaps"
		try:
			f = open(path, "r")
			entire_line = f.readlines()
			f.close()
		except IOError:
			exit()
	
		mgr = smapManager(entire_line)
		mgr.print_attr_in_area(attr,pid)
	sleep(1)


