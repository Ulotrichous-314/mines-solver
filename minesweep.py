import numpy as np
import pyscreenshot as ImageGrab
import matplotlib.pyplot as plt
import cv2
import time
import itertools
import os
import sys
import random
import logging
from PIL import Image
from pymouse import PyMouse

logging.basicConfig(filename='debug.log',level=logging.DEBUG)

class field:
	"""
	Object that descibes each square in the minefield
	"""
	def __init__(self, position=np.zeros(2), size=30):
		self.pos = position
		self.size = size
		self.center = [position[0] + size/2, position[1] + size/2]
		self.clicked = False
		self.mines = '-'
		self.complete = False
		self.dead = False
		self.border = False
		self.prob = 2

	def __repr__(self):
		return 'field('+str(self.pos)+','+str(self.size)+')'

	def scrape(self,image):
		if not self.clicked:
			crop_size = (self.pos[1],self.pos[0],self.pos[1]+self.size-5,self.pos[0]+self.size-5)
			#print crop_size
			image = image.crop(crop_size)
			#plt.imshow(image)
			#plt.show()
			colours = top5Colours(image)
			if colours == False:
				self.dead = True
				self.clicked = True
				self.mines = '#'
			elif (0, 0, 255) in colours:
				self.mines = 1
				self.clicked = True
				self.border = False
			elif (0, 160, 0) in colours:
				self.mines = 2
				self.clicked = True
				self.border = False
			elif (255, 0, 0) in colours:
				self.mines = 3
				self.clicked = True
				self.border = False
			elif (0, 0, 127) in colours:
				self.mines = 4
				self.clicked = True
				self.border = False
			elif (160, 0, 0) in colours:
				self.mines = 5
				self.clicked = True
				self.border = False
			elif (0, 255, 255) in colours:
				self.mines = 6
				self.clicked = True
				self.border = False
			elif (160,0,160) in colours:
				self.mines = 7
				self.clicked = True
				self.border = False
			elif (119,119,119) in colours:
				self.clicked = True
				self.complete = True
				self.mines = 'f'
				self.border = False
			elif (29, 29, 29) in colours:
				self.dead = True
				self.mines = 'X'
			elif len(colours) < 5:
				self.mines = 0
				self.complete = True
				self.clicked = True
			elif min([min(i) for i in colours]) > 200:
				#not clicked
				return
			elif min([min(i) for i in colours]) > 150 and min([min(i) for i in colours]) < 220:
				self.mines = 0
				self.complete = True
				self.clicked = True
			else:
				print 'Error - Field not recognised'
				print colours
				self.dead = True
				plt.imshow(image)
				plt.show()
					

	def flag(self,mouse):
		mouse.click(self.center[1],self.center[0],2)
		self.border = False
		time.sleep(0.1)
		self.complete = True
		self.mines = 'f'
		self.prob = 1
		#time.sleep(1)

	def click(self,mouse):
		if self.mines == '-':
			mouse.click(self.center[1],self.center[0],1)
			mouse.move(self.pos[1]+self.size+2,self.pos[0]+self.size+2)
			self.border = False
			self.prob = 0
			time.sleep(0.1)
			image = ImageGrab.grab()
			self.scrape(image)
			#self.clicked = True
			#time.sleep(1)

class minefield:
	def __init__(self,image,template,mouse=PyMouse(),mines=0,confidence=0.9,v=True):
		result = cv2.matchTemplate(image,template,cv2.TM_CCOEFF_NORMED)
		match_indices = np.arange(result.size)[(result>confidence).flatten()]
		result = np.unravel_index(match_indices,result.shape)
		Flist = []
		self.incomplete = []
		self.border = []
		self.permutations = []
		self.mouse = mouse
		self.alive = True
		self.v = v
		for i in range(0,result[0].shape[0]):
			Flist.append([result[0][i],result[1][i]])
		for i in Flist:
			if i[0] != Flist[0][0]:
				x = Flist.index(i)
				break
		y = len(Flist)/x
		self.fields = np.empty((y,x), dtype=object)
		self.shape = [x,y]
		if mines == 0:
			if self.shape == [8,8]:
				self.mines = 10
			elif self.shape == [16,16]:
				self.mines = 40
			else:
				self.mines = 99
		count = 0
		for iy in range(0,y):
			for ix in range(0,x):
				self.fields[iy,ix] = field(position=Flist[count])
				count+= 1

	def scrapeAll(self,debug=False):
		endField = self.fields.flatten()[-1]
		self.mouse.move(endField.pos[1]+endField.size,endField.pos[0]+endField.size)
		time.sleep(0.1)
		image = ImageGrab.grab()
		for i in self.fields.flatten():
			if i.mines == '-':
				i.scrape(image)
				if i.dead == True:
					self.alive = False
				elif i.clicked and not i.complete:
					self.incomplete.append(i)
				elif not i.border and i in self.border:
					self.border.remove(i)
		if debug:
			self.display()
			plt.imshow(image)
			plt.show()

	def basicAlg(self,field):
		flags, unclicked = [],[]
		near = self.near(field)
		for i in near:
			if i.mines == 'f':
				flags.append(i)
			elif i.mines == '-':
				unclicked.append(i)
				if not i.border:
					self.border.append(i)
					i.border = True
		if field.mines == len(flags):
			for i in unclicked:
				self.border.remove(i)
				i.click(self.mouse)
				if i.mines == '#':
					self.dead = True
				elif i.mines == 0:
					self.scrapeAll()
				else:
					self.incomplete.append(i)
			self.incomplete.remove(field)
			return True
		elif field.mines == len(flags)+len(unclicked):
			for i in unclicked:
				self.border.remove(i)
				i.flag(self.mouse)
				self.mines -= 1
			self.incomplete.remove(field)
			return True
		else:
			return False
			
	def rand(self):
		while True:
			randField = self.fields[random.randint(0,self.shape[1])-1][random.randint(0,self.shape[0])-1]
			if not randField.clicked:
				return randField
				
	def display(self, permutation=False, p=0, hl=[]):
		#self.scrapeAll()
		for y in self.fields:
			for x in y:
				if x in hl:
					sys.stdout.write('!')
				else:
					sys.stdout.write(' ')
				if permutation and x in self.permutations[p]:
					sys.stdout.write('X')
				else:
					sys.stdout.write(str(x.mines))
			sys.stdout.flush()
			print ''
			
	def near(self, field):
		#return all fields near entered field
		near = []
		index = findIndex(self.fields,field)
		y,x = index[0],index[1]
		maxy,maxx = self.shape[1]-1,self.shape[0]-1
		if x != 0 and y != 0:
			near.append(self.fields[y-1][x-1])
		if y != 0:
			near.append(self.fields[y-1][x])
		if y != 0 and x != maxx:
			near.append(self.fields[y-1][x+1])
		if x != 0:
			near.append(self.fields[y][x-1])
		if x != maxx:
			near.append(self.fields[y][x+1])
		if y != maxy and x != 0:
			near.append(self.fields[y+1][x-1])
		if y != maxy:
			near.append(self.fields[y+1][x])
		if y != maxy and x != maxx:
			near.append(self.fields[y+1][x+1])
		return near
		
			
	def bruteForce(self, fields):
		if self.v: print'Starting brute force attempt'
		if self.v: print 'Border: '+str(len(fields))
		near = [] #numbered fields near border
		correct = [] #list of correct permutations
		for i in fields:
			for ii in self.near(i):
				if ii.mines != '-' and ii.mines != 'f':
					near.append(ii)
		maxMines = self.mines
		if len(fields) < maxMines:
			maxMines = len(fields)
		if self.v: print 'maxMines = '+str(maxMines)
		if len(fields) > 15:
			return False
		self.permutations = []
		for mines in range(1,maxMines+1):
			for i in itertools.combinations(fields,mines):
				self.permutations.append(i)
		if self.v: print 'Permutations: '+str(len(self.permutations))
		n=0
		for i in self.permutations:
			if self.v: status((n/float(len(self.permutations)))*100)
			if self.checkGuess(near,i):
				correct.append(i)
				#guess works
			n += 1
		if self.v: print ''
		if self.v: print 'Correct = '+str(len(correct))
		if len(correct) != 0:
			for i in fields:
				i.prob = 0
				for ii in correct:
					if i in ii:
						i.prob += 1
				i.prob = float(i.prob)/len(correct)
		else:
			if self.v: print 'Error - No correct solutions found'
			self.alive = False
		return True
				
	def checkGuess(self,near,mined):
		ans = True
		for i in near:
			mines = 0
			for ii in self.near(i):
				if ii in mined or ii.mines == 'f':
					mines += 1
			if i.mines != mines:
				ans = False
				break 
		return ans
	
	def checkProbs(self):
		found = False
		lowest , low = 1,1
		for i in self.border:
			if i.prob == 0:
				i.click(self.mouse)
				if i.mines == '#':
					self.dead = True
				elif i.mines == 0:
					self.scrapeAll()
				else:
					self.incomplete.append(i)
				self.border.remove(i)
				found = True
			elif i.prob == 1:
				i.flag(self.mouse)
				self.mines -= 1
				self.border.remove(i)
				found = True
			elif i.prob < low:
				lowest = i
				low = i.prob
		if not found:
			lowest.click(self.mouse)
			if i.mines == '#':
				self.dead = True
			elif i.mines == 0:
				self.scrapeAll()
			else:
				self.incomplete.append(i)
		self.scrapeAll()
		
	def group(self):
		border = list(self.border)
		groups = [[border[0]]]
		border.remove(border[0])
		for i in groups:
			for ii in groups:
				for field in border:
					if field in self.near(ii):
						group[i].append(field)
						border.remove(field)
			if len(border) == 0:
				return groups
			else:
				groups.append([border[0]])

def status(percent):
	sys.stdout.write('[')
	for i in range(0,10):
		if percent >= i*10:
			sys.stdout.write('>')
		else:
			sys.stdout.write('-')
	sys.stdout.write(']')
	sys.stdout.write("%3d%%\r" % percent)
	sys.stdout.flush()

def top5Colours(img):
	c = img.getcolors()
	if c == None:
		return False
	else:
		c = sorted(c, key=lambda c: -c[0])
		ans = []
		for i in range(0,5):
			try:
				ans.append(c[i][1])
			except:
				break
		return ans
		
def findIndex(array,item):
	x,y = -1,-1
	for i in array:
		y += 1
		x = -1
		for ii in i:
			x += 1
			if ii == item:
				return [y,x]

def solve(template=cv2.imread("images/field.png"),debug=False,speed=False,mouse=PyMouse(),v=True):
	if not speed:
		sys.stdout.write('Starting in 5 seconds')
		sys.stdout.flush()
		time.sleep(1)
		for i in range(0,4):
			sys.stdout.write('.')
			sys.stdout.flush()
			time.sleep(1)
		print '--Starting'
	img = ImageGrab.grab()
	img.save('tmp.png')
	main = minefield(cv2.imread("tmp.png"),template,mouse,v=v)
	os.remove("tmp.png")
	if not speed:
		print 'Grid found '+str(main.shape)
		print 'Mines: '+str(main.mines)
	start = main.fields[0][0]
	start.click(main.mouse)
	if start.mines == '#':
		main.alive = False
	elif start.mines == 0:
		main.scrapeAll()
	else:
		main.incomplete.append(start)
	while main.alive and main.mines != 0:
		while True:
			click = False
			for i in main.incomplete:
				if main.basicAlg(i):
					click = True
					break
			if not click:
				break
		"""
		rand = main.rand()
		rand.click(main.mouse)
		if rand.dead == True:
			main.alive = False
		elif rand.mines == 0:
			main.scrapeAll()
		else:
			main.incomplete.append(rand)
		"""
		if main.bruteForce(main.border):
			if v: print 'done'
			main.checkProbs()
		else:
			if v: print 'Will take too long'
			if v: print 'Clicking randomly'
			rand = main.rand()
			rand.click(main.mouse)
			if rand.dead == True:
				main.alive = False
			elif rand.mines == 0:
				main.scrapeAll()
			else:
				main.incomplete.append(rand)
		groups = main.group()
		rand = True
		if v: print str(len(groups))+' groups found'
		for group in groups:
			if main.bruteForce(group): rand = False
		if rand:
			
	if debug:
		print 'incomplete: '+str(len(main.incomplete))
	#for i in main.incomplete:
		#print findIndex(main.fields,i)
	if debug:
		main.display()
	if not speed:
		return main
	else:
		return main.alive
		
def speed(number=100,size=99):
	#time.sleep(5)
	sys.stdout.write('Starting in 5 seconds')
	sys.stdout.flush()
	time.sleep(1)
	for i in range(0,4):
		sys.stdout.write('.')
		sys.stdout.flush()
		time.sleep(1)
	print '--Starting'
	m = PyMouse()
	solved, failed = 0,0
	new = cv2.imread("images/new.png")
	win = cv2.imread("images/win.png")
	if size == 99:
		template = cv2.imread("images/99.png")
	elif size == 10:
		template = cv2.imread("images/10.png")
	for i in range(0,number):
		if solve(speed=True,mouse=m,v=False):
			print str(i+1)+' : Solved!'
			solved += 1
			time.sleep(0.5)
			img = ImageGrab.grab()
			img.save('tmp.png')
			image = cv2.imread("tmp.png")
			os.remove("tmp.png")
			result = cv2.matchTemplate(image,win,cv2.TM_CCOEFF_NORMED)
			index = np.unravel_index(result.argmax(),result.shape)
			m.click(index[1],index[0])
			time.sleep(0.5)
		else:
			print str(i+1)+' : Fail'
			failed += 1
			img = ImageGrab.grab()
			img.save('tmp.png')
			image = cv2.imread("tmp.png")
			os.remove("tmp.png")
			result = cv2.matchTemplate(image,new,cv2.TM_CCOEFF_NORMED)
			index = np.unravel_index(result.argmax(),result.shape)
			m.click(index[1],index[0])
			time.sleep(0.5)
		img2 = ImageGrab.grab()
		img2.save('tmp2.png')
		image2 = cv2.imread("tmp2.png")
		os.remove("tmp2.png")
		result2 = cv2.matchTemplate(image2,template,cv2.TM_CCOEFF_NORMED)
		index2 = np.unravel_index(result2.argmax(),result2.shape)
		m.click(index2[1],index2[0])
		time.sleep(0.5)
	print 'Finished'
	print 'Solved: '+str(solved),
	print ' Failed: '+str(failed),
	print ' Success rate: '+str((solved/float(number))*100)+'%'
