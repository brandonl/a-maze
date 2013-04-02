#! /usr/bin/env python

#for `//` which is available in python3
from __future__ 	import division 

import pyglet, sys, heapq, math
from pyglet.gl 		import *
from pyglet.window 	import key, Window, mouse
from pyglet.clock  	import Clock
from pyglet.event 	import EventDispatcher

################################################################Settings####

# Mimic cstyle enums
def enum( **enums ):
	return type( 'Enum', (), enums )

SquareType = enum( EMPTY=1, START=2, BLOCKED=3, GOAL=4, RUNNER=5, TRAIL=6 )


SETTINGS = { 
	'BLOCK_SIZE' : 20,
	'WINDOW_WIDTH' : 800,
	'WINDOW_HEIGHT' : 600,
	'LINE_COLOR':	[ 255, 255, 255, 44, 255, 255, 255, 44 ],
	'EMPTY_COLOR':	[ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ],
	'BLOCKED_COLOR':[ 	255, 255, 255, 160, 255, 255, 255, 160,
						255, 255, 255, 160, 255, 255, 255, 160
					],
	'GOAL_COLOR':	[	204, 102, 102, 150, 204, 102, 102, 150,
						204, 102, 102, 150, 204, 102, 102, 150 
					],
	'START_COLOR':  [	255, 198, 116, 80, 255, 198, 116, 80,
						255, 198, 116, 80, 255, 198, 116, 80 
					],
	'RUNNER_COLOR':	[	255, 255, 80, 80, 255, 255, 80, 80,
						255, 255, 80, 80, 255, 255, 80, 80 
					],
	'TRAIL_COLOR':	[	255, 255, 255, 25, 255, 255, 255, 25,
						255, 255, 255, 25, 255, 255, 255, 25
					],
	'HEURISTIC'	:	'Manhattan'
}

COLOR_OPTIONS = {
	1 : 'EMPTY_COLOR',
	2 :	'START_COLOR',
	3 :	'BLOCKED_COLOR',
	4 :	'GOAL_COLOR',
	5 : 'RUNNER_COLOR',
	6 : 'TRAIL_COLOR'
}

DIRECTIONS = [(-1,0), (-1,1), (0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1)]

###################################################### A P P ##################


class App:
	def __init__(self, size ):
		self.size = size
		self.squares = {}
		padding = SETTINGS['BLOCK_SIZE']
		self.grid = Grid( 	pos=(padding, padding), 
							w=self.size[0]-padding, 
							h=self.size[1]-padding )
		self.setup()

	def setup(self):
		varx = self.grid.x
		bsz = SETTINGS['BLOCK_SIZE']

		while varx < self.grid.width:
			vary = self.grid.y
			while vary < self.grid.height:
				pos = (varx//bsz,vary//bsz )
				self.squares[ pos ] = Square( varx, vary, SquareType.EMPTY )
				vary = vary + self.grid.step
			varx = varx + self.grid.step


	def pressSquare(self, sqr ):
		sqr.updateColor( SquareType.BLOCKED )


class Grid( object ):
	def __init__( self, pos, w, h ):
		self.x = pos[0]
		self.y = pos[1]
		self.width = w
		self.height = h
		self.step = SETTINGS['BLOCK_SIZE']
		self.vertices = [{}]
		self.setup()


	def setup( self ):
		# V e r t i c a l
		self.vertices.pop(0)
		var = self.x
		while var <= self.width:
			self.vertices.append( {	'positions' : [ var, self.y, var, self.height ],
									'colors' 	: SETTINGS['LINE_COLOR'] } )
			var = var + self.step

		# H o r i z o n t a l
		var = self.y
		while var <= self.height:
			self.vertices.append( {	'positions' : [ self.x, var, self.width, var ],
									'colors' 	: SETTINGS['LINE_COLOR'] } )
			var = var + self.step



class Square( object ):
	def __init__(self, x, y, stype ):
		self.x = x
		self.y = y
		self.stype = stype
		self.size = SETTINGS['BLOCK_SIZE']
		self.vertices = {}
		self.setup()


	def setup( self ):
		self.vertices['positions'] 	= [ self.x, self.y, 
										self.x + self.size, self.y,
										self.x + self.size, self.y + self.size,
										self.x, self.y + self.size 
										]

		self.vertices['colors'] 	= SETTINGS[ COLOR_OPTIONS[self.stype] ]


	def updateColor( self, stype ):
		self.stype = stype
		self.vertices['colors'] 	= SETTINGS[ COLOR_OPTIONS[self.stype] ]
		return self.vertices['colors']

############################################ C L I E N T ######################


class ClientGroup(pyglet.graphics.Group):
	def set_state(self):
		glEnable( GL_BLEND )
		glLineWidth( 3.0 )


	def unset_state(self):
		glDisable( GL_BLEND )
		glLineWidth( 1.0 )



class ClientGrid( object ):
	def __init__( self, appGrid ):
		self.appGrid = appGrid
		self.gridBatch = pyglet.graphics.Batch()
		self.setup()


	def setup( self ):
		group = ClientGroup()

		for v in self.appGrid.vertices:
			vlist = self.gridBatch.add( 2, GL_LINES, group, 'v2i/static', 'c4B/static' )
			vlist.vertices = v['positions']
			vlist.colors = v['colors']


	def draw(self):
		self.gridBatch.draw()


	def update(self, dt):	
		pass



class ClientSquare( object ):
	def __init__( self, square, verts ):
		self.square = square
		self.vertList = verts
		self.pos = ( square.x // SETTINGS['BLOCK_SIZE'],
					square.y // SETTINGS['BLOCK_SIZE'] )


	def update( self, stype ):
		self.vertList.colors = self.square.updateColor( stype )



class Client( object ):
    def __init__(self, app):
		self.app = app
		self.window = Window(	width=self.app.size[0],
		        				height=self.app.size[1], 
		        				style='dialog',
		        				resizable=False )

		self.window.set_caption("ASTAR MAZE")
		self.window.on_close = sys.exit
		self.ctrl = InputHandler(self)
		self.window.push_handlers(self.ctrl)

		self.clock = Clock()
		self.clock.set_fps_limit(30)
		self.window.push_handlers(self.clock)

		self.grid = ClientGrid( self.app.grid )

		# S q u a r e s
		self.entities = {}
		self.setup()


    def setup(self):
		glClearColor( .113, .121, .1289, 1 )
		glBlendFunc( GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA )
		glDisable( GL_LIGHTING )
		glCullFace( GL_BACK )
		glDisable( GL_DEPTH_TEST )

		self.runner = None
		self.goal = None
		self.isSearching = False
		self.found = False
		self.solution = []
		self.prev = None

		self.entitiesBatch = pyglet.graphics.Batch()
		group = ClientGroup()
		for k,v in self.app.squares.iteritems():
			verts = self.entitiesBatch.add( 4, GL_QUADS, group, 'v2i/static', 'c4B/dynamic' )
			verts.vertices 		= v.vertices['positions']
			verts.colors 		= v.vertices['colors']
			self.entities[k] 	= ClientSquare( v, verts )


    def draw(self):
		self.grid.draw()
		self.entitiesBatch.draw()
		if self.found: 
			curr = None
			if self.prev:
				self.setVisited( self.entities[self.prev] )
			if len(self.solution):
				curr = self.solution.pop()
				self.entities[curr].update( SquareType.RUNNER )
				self.prev = curr


    def update(self):
        self.clock.tick()
        self.window.dispatch_events()
        self.window.clear()
        self.draw()
        self.window.flip()


    def reset(self):
    	self.app.setup()
    	self.setup()


    def astar(self):
		startState = ASState( self.runner.pos, self.goal.pos, self )
		nodesGenerated = 1
		frontier = Heap()
		expanded = set()
		frontier.push( 0, ASNode( startState ) )

		while len(frontier):
			n = frontier.pop()

			if n.state.isGoal():
				self.solution = n.execute()
				print "%d node(s) generated.\n" % nodesGenerated
				return True

			successors = n.state.expand()
			for succ in successors:
				if succ['successor'] not in expanded:
					nodesGenerated = nodesGenerated + 1
					nprime = ASNode( succ['successor'], succ['action'], n )
					frontier.push( nprime.hCost, nprime )
					expanded.add( succ['successor'] )
		return False


    def search(self):
    	if not self.runner or not self.goal:
    		print "You must select a start and end position on the grid"
    		print "Press 1 and then click a square for start position (in purple)."
    		print "Press 2 and then click a square for end position (in red)."
    	else:
    		self.isSearching = True
    		print "\nRUNNING A*\n"
    		print "Goal position:   \t",		self.goal.pos
    		print "Start position:  \t",		self.runner.pos
    		print "Using heuristic: \t%s\n" 	% SETTINGS['HEURISTIC']

    		if self.astar():
    			self.found = True
    		else:
    			print "Failed to solve maze."
    		self.isSearching = False


    def pressSquare( self, sqr ):
		sqr.update( SquareType.BLOCKED )


    def resetSquare( self, sqr ):
		sqr.update( SquareType.EMPTY )

    
    def setStart( self, sqr ):
    	if not self.runner:
    		sqr.update( SquareType.START )
    		self.runner = sqr


    def setEnd( self, sqr ):
    	if not self.goal:
    		sqr.update( SquareType.GOAL )
    		self.goal = sqr

    def setVisited( self, sqr ):
    	sqr.update( SquareType.TRAIL )


class InputHandler(EventDispatcher):
    def __init__( self, client ):
        EventDispatcher.__init__(self)
        self.client 	= client
        self.setStart 	= False
        self.setEnd 	= False
        self.erase		= False


    def findBlock( self, x, y ):
		point = ( x//SETTINGS['BLOCK_SIZE'], y//SETTINGS['BLOCK_SIZE'] )
		if self.client.entities.has_key(point):
			return self.client.entities[point]


    def on_mouse_press( self, x, y, button, mod ):
    	if not self.client.isSearching:
	    	sqr = self.findBlock( x, y )
	    	if sqr:
	    		if sqr.square.stype == SquareType.EMPTY:
	    			if self.setStart:
	    				self.client.setStart( sqr )
	    				self.setStart = False
	    			elif self.setEnd:
	    				self.client.setEnd( sqr )
	    				self.setEnd = False
	    			else:
	    				self.client.pressSquare( sqr )
	    		elif sqr.square.stype == SquareType.BLOCKED:
	    			self.client.resetSquare( sqr )


    def on_mouse_release( self, x, y, button, mod ):
    	pass


    def on_mouse_drag( self, x, y, dx, dy, buttons, mod ):
    	if not self.client.isSearching:
	    	sqr = self.findBlock( x, y )
	    	if sqr and sqr.square.stype == SquareType.EMPTY:
					self.client.pressSquare( sqr )


    def on_key_press( self, sym, mod ):
    	if not self.client.isSearching:
	    	if sym == key.S and not self.client.found:
	    		self.client.search()
	    	if sym == key.F5:
	    		self.client.reset()
	    		self.client.found = False
	    	if sym == key._1:
	    		self.setStart = not self.setStart
	      	if sym == key._2:
	      		self.setEnd = not self.setEnd
	      	if sym == key._3:
	      		SETTINGS['HEURISTIC'] = 'Manhattan'
	      	if sym == key._4:
	      		SETTINGS['HEURISTIC'] = 'Euclidean'

###############################################################################

# Heap wrapper decorates custom items with a priority
class Heap( object ):
	def __init__(self):
		self.m_heap = []

	def push( self, priority, item ):
		assert priority >= 0
		heapq.heappush( self.m_heap, (priority, item ) )

	def pop( self ):
		return heapq.heappop( self.m_heap )[1]

	def __len__(self):
		return len(self.m_heap)

	def __iter__(self):
		return iter( self.m_heap )




class ASAction( object):
	def __init__(self, pos, cost):
		self.cost = cost
		self.position = pos

	def execute(self):
		return self.position


class ASState( object ):
	def __init__(self, pos, goal, client ):
		self.goal = goal
		self.pos = pos
		self.client = client
		self.minx = client.app.grid.x // client.app.grid.step
		self.miny = client.app.grid.y // client.app.grid.step
		self.maxx = client.app.grid.width // client.app.grid.step - self.minx
		self.maxy = client.app.grid.height //client.app.grid.step - self.miny


	def expand(self):
		successors = []
		for x, y in DIRECTIONS:
			newPos = ( self.pos[0] + x, self.pos[1] + y )
			succ = ASState( newPos, self.goal, self.client )
			if succ.isValidState():
				successors.append( { 'successor' : succ, 
									 'action' : ASAction( newPos, 1 ) } )
		return successors


	def isValidState(self):
		if 	self.pos[0] >= self.minx and self.pos[1] >= self.miny:
			if self.pos[0] <= self.maxx and self.pos[1] <= self.maxy:
				if self.client.app.squares[self.pos].stype == SquareType.EMPTY or self.client.app.squares[self.pos].stype == SquareType.GOAL:
					return True
		return False


	def heuristic(self):
		if SETTINGS['HEURISTIC'] == 'Euclidean':
			return math.sqrt( math.pow( self.pos[0] - self.goal[0], 2 )
						 	+ math.pow( self.pos[1] - self.goal[1], 2 ))

		return abs( self.pos[0] - self.goal[0] ) + abs( self.pos[1] - self.goal[1] )


	def isGoal(self):
		if self.pos == self.goal:
			return True
		return False

	def __hash__(self):
		return hash( self.pos )

	def __eq__(self, other ):
		return self.pos == other.pos


class ASNode( object ):
	def __init__(self, state, action=None, parent=None):
		self.state = state
		self.parent = parent
		self.previousAction = action
		self.gCost = 0
		if parent and action:
			self.gCost = self.parent.gCost + self.previousAction.cost
		self.hCost = self.gCost + self.state.heuristic()

	def estimate(self):
		return self.hCost

	def execute(self):
		path = []
		self.doExecute( path )
		path.pop(0)
		return path


	def doExecute(self, path ):
		if self.parent:
			path.append( self.previousAction.execute() )	
			self.parent.doExecute( path )


if __name__ == '__main__':

	app = App( size=( SETTINGS['WINDOW_WIDTH'], SETTINGS['WINDOW_HEIGHT'] ) )
	client = Client(app)


	while True:
		client.update()

		