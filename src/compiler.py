import sys
sys.dont_write_bytecode = True
from traceback import format_exc
from os.path import exists as path_exists
from copy import deepcopy

get_globals = globals
get_locals = locals

headers_package = path_exists('./headers')

if headers_package:
	from headers.header_common import *
else:
	from header_common import *



class MSException(Exception):

	def formatted(self):
		output = []
		for index in xrange(len(self.args)):
			prefix = '  ' * index
			messages = self.args[index].strip().split('\n')
			for message in messages:
				output.append(prefix)
				output.append(message.strip())
				output.append('\n')
		return ''.join(output)



class AGGREGATE(dict):
	def __or__(self, other):
		result = AGGREGATE(self)
		result.update(other)
		return result
	__add__ = __or__



class VARIABLE(object):

	operations = set(['+', '-', '*', '/', '%', '**', '<<', '>>', '&', '|', '^', 'neg', 'abs', 'val'])

	references = None

	is_expression = False
	is_static = True

	module = None
	name = None
	value = None

	operation = None
	operands = None

	def __init__(self, module = None, name = None, value = None, operation = None, operands = None, static = True):
		self.module = module
		self.name = name
		self.references = set()
		if operation:
			self.operation = operation
			self.operands = operands
			self.is_expression = True
			if static:
				for operand in operands:
					if isinstance(operand, VARIABLE) and not operand.is_static: static = False
			if operation not in VARIABLE.operations: raise SyntaxError('Illegal MSC expression: %r' % self)
		else:
			self.value = value
		self.is_static = static
   
	def __add__(self, other):    return VARIABLE(operands = [self, other], operation = '+')
	def __sub__(self, other):    return VARIABLE(operands = [self, other], operation = '-')
	def __mul__(self, other):    return VARIABLE(operands = [self, other], operation = '*')
	def __div__(self, other):    return VARIABLE(operands = [self, other], operation = '/')
	def __mod__(self, other):    return VARIABLE(operands = [self, other], operation = '%')
	def __pow__(self, other):    return VARIABLE(operands = [self, other], operation = '**')
	def __lshift__(self, other): return VARIABLE(operands = [self, other], operation = '<<')
	def __rshift__(self, other): return VARIABLE(operands = [self, other], operation = '>>')
	def __and__(self, other):    return VARIABLE(operands = [self, other], operation = '&')
	def __or__(self, other):     return VARIABLE(operands = [self, other], operation = '|')

	def __radd__(self, other):    return VARIABLE(operands = [other, self], operation = '+')
	def __rsub__(self, other):    return VARIABLE(operands = [other, self], operation = '-')
	def __rmul__(self, other):    return VARIABLE(operands = [other, self], operation = '*')
	def __rdiv__(self, other):    return VARIABLE(operands = [other, self], operation = '/')
	def __rmod__(self, other):    return VARIABLE(operands = [other, self], operation = '%')
	def __rpow__(self, other):    return VARIABLE(operands = [other, self], operation = '**')
	def __rlshift__(self, other): return VARIABLE(operands = [other, self], operation = '<<')
	def __rrshift__(self, other): return VARIABLE(operands = [other, self], operation = '>>')
	def __rand__(self, other):    return VARIABLE(operands = [other, self], operation = '&')
	def __ror__(self, other):     return VARIABLE(operands = [other, self], operation = '|')

	def __neg__(self): return VARIABLE(operands = [self], operation = 'neg')
	def __pos__(self): return self
	def __abs__(self): return VARIABLE(operands = [self], operation = 'abs')

	def formatted_name(self):
		if self.is_expression: return '<expr>'
		if self.module is None: return '?.%s' % self.name
		return '%s.%s' % (self.module[2], self.name)

	def __str__(self):
		return str(self.__long__())

	def __repr__(self):
		if self.is_expression:
			if len(self.operands) == 1:
				result = '%s(%r)' % (self.operation, self.operands[0])
			else:
				operands = [(('(%r)' if (isinstance(op, VARIABLE) and op.is_expression and (len(op.operands) > 1)) else '%r') % op) for op in self.operands]
				result = (' %s ' % self.operation).join(operands)
		else:
			if self.is_static:
				value = '?' if self.value is None else str(self.value)
				result = '%s[#%s]' % (self.formatted_name(), value)
			else:
				value = '?' if self.value is None else str(self.value)
				result = '%s[@%s]' % (self.formatted_name(), value)
		return '<%s>' % result

	def __long__(self):
		try:
			if self.is_expression:
				if not self.is_static: raise MSException('expression %r is not static and cannot be calculated at compile-time' % self)
				if self.operation == 'neg': return -long(self.operands[0])
				elif self.operation == 'abs': return abs(long(self.operands[0]))
				elif self.operation == 'val': return long(self.operands[0])
				elif self.operation == '+': return long(self.operands[0]) + long(self.operands[1])
				elif self.operation == '-': return long(self.operands[0]) - long(self.operands[1])
				elif self.operation == '*': return long(self.operands[0]) * long(self.operands[1])
				elif self.operation == '/': return long(self.operands[0]) // long(self.operands[1])
				elif self.operation == '%': return long(self.operands[0]) % long(self.operands[1])
				elif self.operation == '**': return long(self.operands[0]) ** long(self.operands[1])
				elif self.operation == '<<': return long(self.operands[0]) << long(self.operands[1])
				elif self.operation == '>>': return long(self.operands[0]) >> long(self.operands[1])
				elif self.operation == '&': return long(self.operands[0]) & long(self.operands[1])
				elif self.operation == '|': return long(self.operands[0]) | long(self.operands[1])
				else: raise MSException('expression %r contains illegal operation %s' % (self, self.operation))
			else:
				if self.value is not None: return self.value
				if self.is_static: raise MSException('identifier %r value is not defined' % self)
				else: raise MSException('variable %r is not allocated' % self)
		except MSException, e:
			raise MSException('failed to calculate expression %r' % self, *e.args)
		except Exception, e:
			raise MSException('failed to calculate expression %r' % self, e.message)

	def __int__(self): return self.__long__()
	def __float__(self): return float(self.__long__())

	def __call__(self, script_name, destination, local_depth):
		try:
			total_commands = 1 # Usually an expression will generate one command
			operations = []
			# Pre-calculate operands
			for index in xrange(len(self.operands)):
				operand = self.operands[index]
				if isinstance(operand, VARIABLE):
					if operand.is_expression and not(operand.is_static):
						tmp_local = opmask_local_variable | EXPORT.get_local_tmp_id(script_name, local_depth)
						new_commands, new_operations = operand(script_name, tmp_local, local_depth)
						operations.extend(new_operations)
						total_commands += new_commands
						self.operands[index] = tmp_local
						local_depth += 1
					else:
						self.operands[index] = long(operand)
			if self.operation   == 'neg': operations.extend([store_sub, 3, destination, 0, self.operands[0]])
			elif self.operation == 'abs':
				operations.extend([assign, 2, destination, self.operands[0], val_abs, 1, destination])
				total_commands += 1 # We generate two commands instead of one with this expression
			elif self.operation == 'val': operations.extend([assign, 2, destination, self.operands[0]])
			elif self.operation == '+'  : operations.extend([store_add, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '-'  : operations.extend([store_sub, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '*'  : operations.extend([store_mul, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '/'  : operations.extend([store_div, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '%'  : operations.extend([store_mod, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '**' : operations.extend([store_pow, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '<<' :
				operations.extend([assign, 2, destination, self.operands[0], val_lshift, 2, destination, self.operands[1]])
				total_commands += 1 # We generate two commands instead of one with this expression
			elif self.operation == '>>' :
				operations.extend([assign, 2, destination, self.operands[0], val_rshift, 2, destination, self.operands[1]])
				total_commands += 1 # We generate two commands instead of one with this expression
			elif self.operation == '&'  : operations.extend([store_and, 3, destination, self.operands[0], self.operands[1]])
			elif self.operation == '|'  : operations.extend([store_or, 2, destination, self.operands[0], self.operands[1]])
			else: raise MSException('expression %r contains illegal operation %s' % (self, self.operation))
			return total_commands, operations
		except MSException:
			raise MSException('failed to generate dynamic code for expression %r' % self, *e.args)
		except Exception, e:
			raise MSException('failed to generate dynamic code for expression %r' % self, e.message)


class UID(list):

	def __init__(self, basename, defaults = {}, opmask = 0):
		# dict(vars), set(unassigned vars), var_category_name, dict(default_settings_for_new_vars), allow_declaring_new_vars
		super(UID, self).__init__([{}, set(), basename, defaults, True, opmask])

	def __getattr__(self, name):
		#name = name.lower()
		try:
			variable = self[0][name]
		except KeyError:
			if not self[4]: raise MSException('cannot create %s.%s - dynamic entity creation has been disabled for %s' % (self[2], name, self[2]))
			self[0][name] = variable = VARIABLE(module = self, name = name, **self[3])
			self[1].add(name)
		if EXPORT.current_module: variable.references.add(EXPORT.current_module)
		return variable

	#def __getattribute__(self, name):
	#	if name in ('count', 'index'): raise AttributeError() # Prevent standard methods from working on UID. These two names are thus allowed to be used as uid names.
	#	return super(UID, self).__getattribute__(name)

	def __setattr__(self, name, value):
		#name = name.lower()
		try:
			self[0][name].value = value
		except KeyError:
			if not self[4]: raise MSException('cannot create %s.%s = %r - dynamic entity creation has been disabled for %s' % (self[2], name, value, self[2]))
			self[0][name] = VARIABLE(module = self, name = name, value = value, **self[3])
		try: self[1].remove(name)
		except KeyError: pass



class EXPORT(object):

	initialized = False

	destination = './'
	current_module = None

	l = UID('l', { 'static': False })
	g = UID('g', { 'static': False })
	anim = UID('anim')
	fac = UID('fac')
	ip = UID('ip')
	itm = UID('itm')
	icon = UID('icon')
	mnu = UID('mnu')
	mesh = UID('mesh')
	mt = UID('mt')
	track = UID('track')
	psys = UID('psys')
	p = UID('p')
	pt = UID('pt')
	pfx = UID('pfx')
	prsnt = UID('prsnt')
	qst = UID('qst')
	spr = UID('spr')
	scn = UID('scn')
	script = UID('script')
	skl = UID('skl')
	snd = UID('snd')
	s = UID('s', opmask = tag_string << op_num_value_bits)
	tableau = UID('tableau')
	trp = UID('trp')
	registers = UID('reg', { 'static': False })
	qstrings = UID('qstr', { 'static': False })
	imod = UID('imod')
	imodbit = UID('imodbit')

	# COMPILED MODULE EXPORT
	variables = None
	quick_strings = None

	animations = None
	dialogs = None
	dialog_states = None
	factions = None
	game_menus = None
	info_pages = None
	items = None
	map_icons = None
	meshes = None
	mission_templates = None
	tracks = None
	particle_systems = None
	parties = None
	party_templates = None
	postfx_params = None
	presentations = None
	quests = None
	scene_props = None
	scenes = None
	scripts = None
	simple_triggers = None
	skills = None
	skins = None
	sounds = None
	strings = None
	tableaus = None
	triggers = None
	troops = None

	item_modifiers = None

	variables_modified = False
	qstrings_modified = False

	# SUPPORT FOR TROOP UPGRADES
	upgrades = []

	# SUPPORT FOR QUICK STRINGS
	qstr_ktv = {}
	qstr_vtv = {}
	qstr_seq = []

	# SUPPORT FOR DIALOG STATES
	dialog_states_list = ['start','party_encounter','prisoner_liberated','enemy_defeated','party_relieved','event_triggered','close_window','trade','exchange_members', 'trade_prisoners','buy_mercenaries','view_char','training','member_chat','prisoner_chat']
	dialog_states_dict = dict([(dialog_states_list[index], index) for index in xrange(len(dialog_states_list))])
	dialog_uids = {}

	# PLUGIN SUPPORT
	plugins = []
	requirements = {} # To track what plugins are required by other plugins, and fail compilation if requirements are not met
	injections = {}
	injected = set() # To track what injections were actually used, as any non-injected elements may potentially break the module

	# WARNINGS DURING COMPILATION
	errors = []
	warnings = []
	notices = []

	# SUPPORT FOR GLOBAL VARIABLES
	globals_list = []
	deprecated = set()
	uninitialized = set()

	# SUPPORT FOR LOCAL VARIABLES DURING SCRIPT COMPILATION
	local_uses = {}
	local_tmp_uses = []
	local_last_id = -1
	local_128_vars_warning_issued = False

	@classmethod
	def start_script(cls):
		cls.local_uses = {}
		cls.local_tmp_uses = []
		cls.local_last_id = -1
		cls.local_128_vars_warning_issued = False

	@classmethod
	def get_local_id(cls, script_name, name):
		try:
			return cls.local_uses[name]
		except KeyError:
			cls.local_last_id += 1
			cls.local_uses[name] = cls.local_last_id
			if (cls.local_last_id > 127) and not cls.local_128_vars_warning_issued:
				cls.warnings.append('Code object <%r> using more than 128 local variables.' % script_name)
				cls.local_128_vars_warning_issued = True
			return cls.local_last_id

	@classmethod
	def get_local_tmp_id(cls, script_name, index):
		try:
			return cls.local_tmp_uses[index]
		except IndexError:
			cls.local_last_id += 1
			cls.local_tmp_uses.append(cls.local_last_id)
			if (cls.local_last_id > 127) and not cls.local_128_vars_warning_issued:
				cls.warnings.append('Code object <%r> using more than 128 local variables.' % script_name)
				cls.local_128_vars_warning_issued = True
			return cls.local_last_id



def register_plugin(name):
	EXPORT.plugins.append(name)
	EXPORT.current_module = name

def require_plugin(*plugins):
	for plugin in plugins:
		EXPORT.requirements.setdefault(plugin, set()).add(EXPORT.current_module)

def undefined_identifiers():
	undefined = []
	for uidlist in REQUIRED_UIDS.itervalues():
		for varname in uidlist[1]:
			undefined.append((uidlist[0][varname].formatted_name(), uidlist[0][varname].references))
	return undefined

def external_string(value):
	return value.replace(' ', '_').replace('\t', '_')

def external_identifier(name, lowercase = True):
	name = name.replace(" ","_").replace("'","_").replace("`","_").replace("(","_").replace(")","_").replace("-","_").replace(",","").replace("|","").replace("\t","_")
	return name.lower() if lowercase else name

def internal_identifier(name):
	name = external_identifier(name).replace('=','_')
	#if name[0] not in 'abcdefghijklmnopqrstuvwxyz_': name = ''.join(['_', name])
	return name


def calculate_identifiers(source, uid, mask_uid = None, *argl):
	index = -1
	try:
		opmask = uid[5]
		for index in xrange(len(source)):
			name = internal_identifier(source[index][0])
			setattr(uid, name, index | opmask)
			if mask_uid:
				setattr(mask_uid, name, 1 << index)
	except MSException, e:
		raise MSException('failed to parse identifier for %r element #%d' % (uid[2], index), *e.args)
	except Exception, e:
		raise MSException('failed to parse identifier for %r element #%d' % (uid[2], index), e.message)
	uid[4] = False
	if mask_uid: mask_uid[4] = False


def allocate_quick_strings():
	qstr = []
	try:
		try:
			strings_file = open('%s/quick_strings.txt' % EXPORT.destination)
			qstr = [line.strip().split(' ', 1) for line in strings_file.readlines() if line.strip()]
			strings_file.close()
		except IOError:
			pass
		index = 0
		for q in qstr:
			if len(q) > 1:
				EXPORT.qstr_seq.append(q[0])
				EXPORT.qstr_ktv[q[0]] = q[1]
				q_name = 'qs%d' % index
				setattr(qstrings, q_name, opmask_quick_string | index)
				EXPORT.qstr_vtv[q[1]] = getattr(qstrings, q_name)
				index += 1
	except MSException, e:
		raise MSException('failed to allocate quick strings', *e.args)
	except Exception, e:
		raise MSException('failed to allocate quick strings', e.message)
		
def allocate_global_variables(enforce_sgc = True):
	max_global_index = 0
	globals_list = []
	if enforce_sgc:
		try:
			variables_file = open('%s/variables.txt' % EXPORT.destination)
			globals_list = [line.strip() for line in variables_file.readlines() if line.strip()]
			variables_file.close()
		except IOError:
			pass
		except Exception, e:
			raise MSException('general error reading %s/variables.txt file' % EXPORT.destination, format_exc())
	try:
		for var_name in globals_list:
			#print 'Variable %r has default index %d' % (var_name, max_global_index)
			EXPORT.g.__setattr__(var_name, opmask_variable|max_global_index)
			EXPORT.uninitialized.add(var_name)
			max_global_index += 1
	except Exception, e:
		args = e.args if isinstance(e, MSException) else []
		raise MSException('failed to allocate global variable `%s`' % var_name, *args)
	# FIX: THIS IS TOO EARLY TO EXPORT GLOBALS, SOME MAY STILL BE PARSED FROM TEXT! NEED TO MOVE CODE BELOW TO EXPORT PHASE
	try:
		new_vars = list(EXPORT.g[1])
	except Exception, e:
		raise MSException('failed to allocate global variable `%s`' % var_name)
	try:
		for var_name in new_vars:
			#print 'New variable %r given index %d' % (var_name, max_global_index)
			globals_list.append(var_name)
			EXPORT.uninitialized.add(var_name)
			EXPORT.g.__setattr__(var_name, opmask_variable|max_global_index)
			max_global_index += 1
	except Exception, e:
		args = e.args if isinstance(e, MSException) else []
		raise MSException('failed to allocate new global variable `%s`' % var_name, *args)
	EXPORT.globals_list = globals_list
	#globals_list.append('')
	#EXPORT.variables = '\r\n'.join(globals_list)


def preprocess_entities_internal(glob):
	for module, base, upg1, upg2 in EXPORT.upgrades:
		if module is None: module = 'main_module'
		if not isinstance(base, VARIABLE): base = convert_string_id_to_variable(base, EXPORT.trp)
		if not isinstance(upg1, VARIABLE): upg1 = convert_string_id_to_variable(upg1, EXPORT.trp)
		if upg2 and not(isinstance(upg2, VARIABLE)): upg2 = convert_string_id_to_variable(upg2, EXPORT.trp)
		if (base.value is None) or (upg1.value is None) or (upg2 != 0) and (upg2.value is None):
			if upg2: raise MSException('illegal upgrade in %s: %s not defined in upgrade(%s, %s, %s)', module, base.formatted_name(), base.formatted_name(), upg1.formatted_name(), upg2.formatted_name())
			else:    raise MSException('illegal upgrade in %s: %s not defined in upgrade(%s, %s)', module, base.formatted_name(), base.formatted_name(), upg1.formatted_name())
		try:
			troop_tuple = glob['troops'][base.value]
			troop_tuple[14] = upg1.value
			if upg2: troop_tuple[15] = upg2.value
		except Exception, e:
			raise MSException('upgrade operation failed', formatted_exception())

def preprocess_entities(*argl):
	pass

def aggregate_simple(entities):
	entities.insert(0, '%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)

def process_animations(e, index):
	result = [' %s %s %s  %d' % (e[0], e[1], e[2], len(e[3]))]
	if e[3]:
		for se in e[3]:
			result.append('  %f %s %s %s %s %s %f %f %f %f ' % (se[0], se[1], se[2], se[3], se[4], se[5], se[6][0], se[6][1], se[6][2], se[7]))
	else:
		result.append('  none 0 0')
	return '\r\n'.join(result)

def process_info_pages(entity, index):
	return 'ip_%s %s %s' % (entity[0], external_string(entity[1]), external_string(entity[2]))
def aggregate_info_pages(entities):
	entities.insert(0, 'infopagesfile version 1\r\n%d' % len(entities))
	entities.append(' ')
	return '\r\n'.join(entities)

def process_meshes(entity, index):
	return 'mesh_%s %s %s %f %f %f %f %f %f %f %f %f' % tuple(entity)

def process_music(entity, index):
	return '%s %s %s' % (entity[1], entity[2], entity[2] | entity[3])

def process_postfx_params(e, index):
	return 'pfx_%s %s %s  %f %f %f %f  %f %f %f %f  %f %f %f %f' % (e[0], e[1], e[2], e[3][0], e[3][1], e[3][2], e[3][3], e[4][0], e[4][1], e[4][2], e[4][3], e[5][0], e[5][1], e[5][2], e[5][3])
def aggregate_postfx_params(entities):
	entities.insert(0, 'postfx_paramsfile version 1\r\n%d' % len(entities))
	entities.append(' ')
	return '\r\n'.join(entities)

def process_quests(e, index):
	return 'qst_%s %s %s %s ' % (e[0], external_string(e[1]), e[2], external_string(e[3]))
def aggregate_quests(entities):
	entities.insert(0, 'questsfile version 1\r\n%d' % len(entities))
	entities.append(' ')
	return '\r\n'.join(entities)

def process_skills(e, index):
	return 'skl_%s %s %s %s %s' % (e[0], external_string(e[1]), e[2], e[3], external_string(e[4]))

def process_strings(e, index):
	return 'str_%s %s' % (e[0], external_string(e[1]))
def aggregate_strings(entities):
	entities.insert(0, 'stringsfile version 1\r\n%d' % len(entities))
	entities.append(' ')
	return '\r\n'.join(entities)

def process_ui_strings(e, index):
	return 'ui_%s|%s' % (e[0], e[1])
def aggregate_ui_strings(entities):
	entities.append('')
	return '\r\n'.join(entities)

def process_user_hints(e, index):
	return 'hint_%d|%s' % (index+1, e[0])

def process_factions(e, index):
    st = 'fac_%s %s %s %s ' % (e[0], external_string(e[1]), e[2], e[6])
    relations = {}
    for target, relation in e[4]:
    	if type(target) == str: target = getattr(EXPORT.fac, target)
    	relations[int(target)] = relation
    return [st, relations, e[3]]
def aggregate_factions(entities):
	for index in xrange(len(entities)):
		rels = [0.0] * len(entities)
		for key, value in entities[index][1].iteritems():
			rels[key] = value
			entities[key][1][index] = value
		rels[index] = entities[index][2]
		entities[index][1] = rels
	for index in xrange(len(entities)):
		entities[index] = '%s\r\n%s\r\n0 ' % (entities[index][0], ''.join([' %f ' % fr for fr in entities[index][1]]))
	entities.insert(0, 'factionsfile version 1\r\n%d\r\n' % len(entities))
	return ''.join(entities)

def process_parties(e, index):
	return ' 1 %d %d p_%s %s %d %d %d %d %d %d %d %d %d %f %f %f %f %f %f 0.0 %d %s\r\n%f' % (index, index, e[0], external_string(e[1]), e[2], e[3], e[4], e[5], e[6], e[6], e[7], e[8], e[8], e[9][0], e[9][1], e[9][0], e[9][1], e[9][0], e[9][1], len(e[10]), ''.join(['%d %d 0 %d ' % (ti[0], ti[1], ti[2]) for ti in e[10]]), 0.0174533 * float(e[11]))
def aggregate_parties(entities):
	entities.insert(0, 'partiesfile version 1\r\n%d %d' % (len(entities), len(entities)))
	entities.append(' ')
	return '\r\n'.join(entities)

def process_party_templates(e, index):
	troops = ' '.join([(('%d %d %d %d' % tuple(e[6][i])) if i < len(e[6]) else '-1') for i in xrange(6)])
	return 'pt_%s %s %d %d %d %d %s ' % (e[0], external_string(e[1]), e[2], e[3], e[4], e[5], troops)
def aggregate_party_templates(entities):
	entities.insert(0, 'partytemplatesfile version 1\r\n%d' % len(entities))
	entities.append(' ')
	return '\r\n'.join(entities)

def process_scenes(e, index):
	return 'scn_%s %s %s %s %s %f %f %f %f %f %s \r\n  %s %s\r\n  %s %s\r\n %s ' % (e[0], external_string(e[0]), e[1], e[2], e[3], e[4][0], e[4][1], e[5][0], e[5][1], e[6], e[7], len(e[8]), (' %d ' * len(e[8])) % tuple(e[8]), len(e[9]), (' %d ' * len(e[9])) % tuple(e[9]), e[10])
def aggregate_scenes(entities):
	entities.insert(0, 'scenesfile version 1\r\n %d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)

def process_particle_systems(e, index):
	return 'psys_%s %s %s  %s %f %f %f %f %f \r\n%f %f   %f %f\r\n%f %f   %f %f\r\n%f %f   %f %f\r\n%f %f   %f %f\r\n%f %f   %f %f\r\n%f %f %f   %f %f %f   %f \r\n%f %f ' % (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9][0], e[9][1], e[10][0], e[10][1], e[11][0], e[11][1], e[12][0], e[12][1], e[13][0], e[13][1], e[14][0], e[14][1], e[15][0], e[15][1], e[16][0], e[16][1], e[17][0], e[17][1], e[18][0], e[18][1], e[19][0], e[19][1], e[19][2], e[20][0], e[20][1], e[20][2], e[21], e[22], e[23])
def aggregate_particle_systems(entities):
	entities.insert(0, 'particle_systemsfile version 1\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)

def process_troops(e, index):
	result = ['trp_%s %s %s %s %s %s %s %d %s %s' % (e[0], external_string(e[1]), external_string(e[2]), external_string(e[13]), e[3], e[4], e[5], e[6], e[14], e[15])]
	result.append('  ' + ''.join([('%d %d ' % ((e[7][i][0], e[7][i][1] << 24) if i < len(e[7]) else (-1, 0))) for i in xrange(64)]))
	if not isinstance(e[8], AGGREGATE): e[8] = unparse_attr_aggregate(e[8])
	if not isinstance(e[9], AGGREGATE): e[9] = unparse_wp_aggregate(e[9])
	result.append('  %d %d %d %d %d' % (e[8].get('str', 0), e[8].get('agi', 0), e[8].get('int', 0), e[8].get('cha', 0), e[8].get('level', 1)))
	result.append((' %d' * num_weapon_proficiencies) % tuple([e[9][index] for index in xrange(num_weapon_proficiencies)]))
	result.append(''.join(['%d ' % ((e[10] >> (32*i)) & 0xFFFFFFFF) for i in xrange(num_skill_words)]))
	face_words = []
	for face_key in (e[11], e[12]):
		word_keys = []
		for word_no in xrange(4):
			word_keys.append((face_key >> (64 * word_no)) & 0xFFFFFFFFFFFFFFFF)
		for word_no in xrange(4):
			face_words.append("%d "%(word_keys[3 - word_no]))
	result.append('  %s\r\n' % ''.join(face_words))
	return '\r\n'.join(result)
def aggregate_troops(entities):
	entities.insert(0, 'troopsfile version 2\r\n%d ' % len(entities))
	return '\r\n'.join(entities)
def process_sounds(entity, index):
	return entity
def aggregate_sounds(entities):
	sound_files = {} # filename -> index
	files = []
	sounds = []
	for sound in entities:
		refs = []
		for f in sound[2]:
			try:
				refs.append('%s 0 ' % sound_files[f])
			except KeyError:
				sound_files[f] = len(files)
				refs.append('%d 0 ' % len(files))
				files.append(' %s %s' % (f, sound[1]))
		sounds.append('snd_%s %s %d %s' % (sound[0], sound[1], len(refs), ''.join(refs)))
	return 'soundsfile version 3\r\n%d\r\n%s\r\n%d\r\n%s\r\n' % (len(files), '\r\n'.join(files), len(sounds), '\r\n'.join(sounds))
def process_skins(e, index):
	skinkeys = [('skinkey_%s %s %s %f %f %s ' % (internal_identifier(sk[4]), sk[0], sk[1], sk[2], sk[3], external_string(sk[4]))) for sk in e[6]]
	beards = ('  %s\r\n' * len(e[8])) % tuple(e[8])
	hair_textures = '  '.join([str(len(e[9]))] + e[9])
	beard_textures = '  '.join([str(len(e[10]))] + e[10])
	face_textures = [' %d ' % len(e[11])]
	for face in e[11]:
		face_textures.append(' %s %s %d %d ' % (face[0], face[1], len(face[2]), len(face[3])))
		face_textures.append((' %s ' * len(face[2])) % tuple(face[2]))
		face_textures.append((' %s ' * len(face[3])) % tuple(face[3]))
	voices = '  '.join([str(len(e[12]))] + [('%d snd_%s' % (v[0], v[1].name)) for v in e[12]])
	constraints = []
	for c in e[17]:
		cvalues = ''.join([' %f %d' % (cvalue[0], cvalue[1]) for cvalue in c[2]])
		constraints.append('%f %d %s %s' % (c[0], c[1], len(c[2]), cvalues))
	constraints = '\r\n'.join(constraints)
	return '%s %s\r\n %s %s %s\r\n %s %s %s\r\n%s\r\n %s \r\n %s\r\n%s\r\n %s \r\n %s \r\n%s\r\n %s \r\n %s %f \r\n%d %d\r\n%s\r\n\r\n%s' % (e[0], e[1], e[2], e[3], e[4], e[5], len(e[6]), ''.join(skinkeys), len(e[7]), '  '.join(e[7]), len(e[8]), beards, hair_textures, beard_textures, ''.join(face_textures), voices, e[13], e[14], e[15], e[16], len(e[17]), constraints)
def aggregate_skins(entities):
	entities.insert(0, 'skins_file version 1\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_scripts(entity, index):
	#return entity
	try: return '%s -1\r\n %s ' % (entity[0], parse_module_code(entity[1], 'script.%s' % entity[0]))
	except MSException, e: raise MSException('failed to compile script %s (#%d)' % (entity[0], index), *e.args)
def aggregate_scripts(entities):
	#return None
	entities.insert(0, 'scriptsfile version 1\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_items(e, index):
	output = [' itm_%s %s %s %d  %s  %s %s %s %s ' % (e[0], external_string(e[1]), external_string(e[1]), len(e[2]), '  '.join(['%s %s' % (imesh[0], imesh[1]) for imesh in e[2]]), e[3], e[4], e[5], e[7])]
	if not isinstance(e[6], AGGREGATE): e[6] = unparse_item_aggregate(e[6])
	if e[6].get('abundance', 0) == 0: e[6]['abundance'] = 100
	output.append('%f %s %s %s %s %s %s %s %s %s %s %s %s' % (e[6].get('weight', 0.0), e[6].get('abundance', 0), e[6].get('head', 0), e[6].get('body', 0), e[6].get('leg', 0), e[6].get('diff', 0), e[6].get('hp', 0), e[6].get('speed', 0), e[6].get('msspd', 0), e[6].get('size', 0), e[6].get('qty', 0), e[6].get('thrust', 0), e[6].get('swing', 0)))
	output.append('\r\n %d' % len(e[9]))
	if len(e[9]):
		output.append('\r\n')
		output.append(''.join([' %d' % faction for faction in e[9]]))
	output.append('\r\n%d\r\n' % len(e[8]))
	for trigger, code_block in e[8]:
		try: output.append('%f  %s\r\n' % (trigger, parse_module_code(code_block, 'itm.%s(#%d).%s' % (e[0], index, trigger_to_string(trigger)))))
		except MSException, er: raise MSException('failed to compile trigger for item %s (#%d)' % (e[0], index), *er.args)
	return ''.join(output)
def aggregate_items(entities):
	entities.insert(0, 'itemsfile version 3\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_map_icons(e, index):
	output = ['%s %s %s %f %d %f %f %f %d' % (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], len(e[8]))]
	for trigger, code_block in e[8]:
		try: output.append('%f  %s ' % (trigger, parse_module_code(code_block, 'icon.%s(#%d).%s' % (e[0], index, trigger_to_string(trigger)))))
		except MSException, er: raise MSException('failed to compile trigger for map icon %s (#%d)' % (e[0], index), *er.args)
	output.append('\r\n')
	return '\r\n'.join(output)
def aggregate_map_icons(entities):
	entities.insert(0, 'map_icons_file version 1\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_scene_props(e, index):
	output = ['spr_%s %s %s %s %s %d' % (e[0], e[1], get_spr_hit_points(e[1]), e[2], e[3], len(e[4]))]
	for trigger, code_block in e[4]:
		try: output.append('%f  %s ' % (trigger, parse_module_code(code_block, 'spr.%s(#%d).%s' % (e[0], index, trigger_to_string(trigger)))))
		except MSException, er: raise MSException('failed to compile trigger for scene prop %s (#%d)' % (e[0], index), *er.args)
	output.append('\r\n')
	return '\r\n'.join(output)
def aggregate_scene_props(entities):
	entities.insert(0, 'scene_propsfile version 1\r\n %d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_simple_triggers(e, index):
	try: return '%f  %s ' % (e[0], parse_module_code(e[1], 'simple_trigger(#%d).%s' % (index, trigger_to_string(e[0]))))
	except MSException, er: raise MSException('failed to compile simple trigger #%d' % (index), *er.args)
def aggregate_simple_triggers(entities):
	entities.insert(0, 'simple_triggers_file version 1\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_tableaus(e, index):
	try: return 'tab_%s %s %s %s %s %s %s %s %s %s ' % (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], parse_module_code(e[9], 'tableau.%s(#%d)' % (e[0], index)))
	except MSException, er: raise MSException('failed to compile tableau %s (#%d)' % (e[0], index), *er.args)
def process_triggers(e, index):
	try: return '%f %f %f  %s  %s ' % (e[0], e[1], e[2], parse_module_code(e[3], 'trigger(#%d).%s.condition' % (index, trigger_to_string(e[0]))), parse_module_code(e[4], 'trigger(#%d).%s.body' % (index, trigger_to_string(e[0]))))
	except MSException, er: raise MSException('failed to compile trigger #d' % (index), *er.args)
def aggregate_triggers(entities):
	entities.insert(0, 'triggersfile version 1\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_presentations(e, index):
	output = ['prsnt_%s %s %s %d' % (e[0], e[1], e[2], len(e[3]))]
	for trigger, code_block in e[3]:
		try: output.append('%f  %s ' % (trigger, parse_module_code(code_block, 'prsnt.%s(#%d).%s' % (e[0], index, trigger_to_string(trigger)))))
		except MSException, er: raise MSException('failed to compile trigger for presentation %s (#%d)' % (e[0], index), *er.args)
	output.append('\r\n')
	return '\r\n'.join(output)
def aggregate_presentations(entities):
	entities.insert(0, 'presentationsfile version 1\r\n %d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_mission_templates(e, index):
	output = ['mst_%s %s %s  %s\r\n%s \r\n\r\n%d ' % (e[0], e[0], e[1], e[2], external_string(e[3]), len(e[4]))]
	for epd in e[4]:
		output.append('%s %s %s %s %s %d %s \r\n' % (epd[0], epd[1], epd[2], epd[3], epd[4], len(epd[5]), (' %s' * len(epd[5])) % tuple(epd[5])))
	output.append(str(len(e[5])))
	output = [''.join(output)]
	for t0, t1, t2, script1, script2 in e[5]:
		try: output.append('%f %f %f  %s  %s ' % (t0, t1, t2, parse_module_code(script1, 'mt.%s(#%d).%s.condition' % (e[0], index, trigger_to_string(t0))), parse_module_code(script2, 'mt.%s(#%d).%s.body' % (e[0], index, trigger_to_string(t0)))))
		except MSException, er: raise MSException('failed to compile trigger for mission template %s (#%d)' % (e[0], index), *er.args)
	output.append('\r\n')
	return '\r\n'.join(output)
def aggregate_mission_templates(entities):
	entities.insert(0, 'missionsfile version 1\r\n %d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_game_menus(e, index):
	try: output = ['menu_%s %s %s none %s %d\r\n' % (e[0], e[1], external_string(e[2]), parse_module_code(e[4], 'mnu.%s(#%d)'%(e[0],index)), len(e[5]))]
	except MSException, er: raise MSException('failed to compile entry code for menu %s (#%d)' % (e[0], index), *er.args)
	for mno in e[5]:
		last_text = mno[4]
		if not last_text: last_text = '.'
		try: output.append(' mno_%s  %s  %s  %s  %s ' % (mno[0], parse_module_code(mno[1], 'mnu.%s(#%d).mno_%s.condition'%(e[0],index,mno[0])), external_string(mno[2]), parse_module_code(mno[3], 'mnu.%s(#%d).mno_%s.choice'%(e[0],index,mno[0])), external_string(last_text)))
		except MSException, er: raise MSException('failed to compile code for menu item %s in menu %s (#%d)' % (mno[0], e[0], index), *er.args)
	return ''.join(output)
def aggregate_game_menus(entities):
	entities.insert(0, 'menusfile version 1\r\n %d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_dialogs(e, index):
	try:
		dialog_state = EXPORT.dialog_states_dict[e[1]]
	except KeyError:
		dialog_state = len(EXPORT.dialog_states_list)
		EXPORT.dialog_states_dict[e[1]] = dialog_state
		EXPORT.dialog_states_list.append(e[1])
	try:
		target_state = EXPORT.dialog_states_dict[e[4]]
	except KeyError:
		target_state = len(EXPORT.dialog_states_list)
		EXPORT.dialog_states_dict[e[4]] = target_state
		EXPORT.dialog_states_list.append(e[4])
	dialog_uid = 'dlga_%s:%s' % (e[1], e[4])
	if (dialog_uid in EXPORT.dialog_uids) and (EXPORT.dialog_uids[dialog_uid] != e[3]):
		new_uid = dialog_uid
		iterator = 0
		while (new_uid in EXPORT.dialog_uids) and (EXPORT.dialog_uids[new_uid] != e[3]):
			iterator += 1
			new_uid = '%s.%d' % (dialog_uid, iterator)
		dialog_uid = new_uid
	EXPORT.dialog_uids[dialog_uid] = e[3]
	try: return '%s %d %d  %s %s  %d  %s %s ' % (dialog_uid, e[0], dialog_state, parse_module_code(e[2], 'dialog.%s(#%d).condition'%(e[1],index)), external_string(e[3]), target_state, parse_module_code(e[5], 'dialog.%s(#%d).result'%(e[1],index)), e[6])
	except MSException, er: raise MSException('failed to compile code for dialog %s (#%d)' % (dialog_uid, index), *er.args)
def aggregate_dialogs(entities):
	entities.insert(0, 'dialogsfile version 2\r\n%d' % len(entities))
	entities.append('')
	return '\r\n'.join(entities)
def process_item_modifiers(e, index):
	return 'imod_%s %s %.06f %.06f' % (e[0], external_string(e[1]), e[2], e[3])
def aggregate_item_modifiers(entities):
	entities.append('')
	return '\r\n'.join(entities)


def postprocess_entities():
	EXPORT.dialog_states_list.append('')
	EXPORT.dialog_states = '\r\n'.join(EXPORT.dialog_states_list)
	output = [str(len(EXPORT.qstr_seq))]
	for qkey in EXPORT.qstr_seq:
		output.append('%s %s' % (qkey, EXPORT.qstr_ktv[qkey]))
	output.append('')
	EXPORT.quick_strings = '\r\n'.join(output)
	EXPORT.globals_list.append('')
	EXPORT.variables = '\r\n'.join(EXPORT.globals_list)



if not EXPORT.initialized:
	REPEATABLE = object()
	SCRIPT = object()

class inject(object):
	name = None
	def __init__(self, name):
		self.name = name

class troop_item(object): pass
def OPTIONAL(check, fallback = None): return { 'check': check, 'default': fallback }

TRIGGER = (float, float, float, SCRIPT, SCRIPT)

parsers = {
	'animations':        { 'parser': (id, int, int, REPEATABLE, (float, id, int, int, int, OPTIONAL(int, 0), OPTIONAL((float, float, float), (0, 0, 0)), OPTIONAL(float, 0))), 'processor': process_animations, 'aggregator': aggregate_simple },
	'dialogs':           { 'parser': (int, id, SCRIPT, str, id, SCRIPT, OPTIONAL(str, 'NO_VOICEOVER')), 'processor': process_dialogs, 'aggregator': aggregate_dialogs, 'uid': 1 },
	'factions':          { 'parser': (id, str, int, float, [(id, float)], [str], OPTIONAL(int, 0xAAAAAA)), 'processor': process_factions, 'aggregator': aggregate_factions },
	'game_menus':        { 'parser': (id, int, str, 'none', SCRIPT, [(id, SCRIPT, str, SCRIPT, OPTIONAL(str, ''))]), 'processor': process_game_menus, 'aggregator': aggregate_game_menus },
	'info_pages':        { 'parser': (id, str, str), 'processor': process_info_pages, 'aggregator': aggregate_info_pages },
	'items':             { 'parser': (id, str, [(id, int)], int, int, int, AGGREGATE, int, OPTIONAL([(float, SCRIPT)], []), OPTIONAL([int], [])), 'processor': process_items, 'aggregator': aggregate_items },
	'map_icons':         { 'parser': (id, int, id, float, int, OPTIONAL(float, 0), OPTIONAL(float, 0), OPTIONAL(float, 0), OPTIONAL([(float, SCRIPT)], []) ), 'processor': process_map_icons, 'aggregator': aggregate_map_icons },
	'meshes':            { 'parser': (id, int, id, float, float, float, float, float, float, float, float, float), 'processor': process_meshes, 'aggregator': aggregate_simple },
	'mission_templates': { 'parser': (id, int, int, str, [(int, int, int, int, int, [int])], [TRIGGER]), 'processor': process_mission_templates, 'aggregator': aggregate_mission_templates },
	'tracks':            { 'parser': (id, file, int, int), 'processor': process_music, 'aggregator': aggregate_simple },
	'particle_systems':  { 'parser': (id, int, id, int, float, float, float, float, float, (float, float), (float, float), (float, float), (float, float), (float, float), (float, float), (float, float), (float, float), (float, float), (float, float), (float, float, float), (float, float, float), float, OPTIONAL(float, 0), OPTIONAL(float, 0)), 'processor': process_particle_systems, 'aggregator': aggregate_particle_systems },
	'parties':           { 'parser': (id, str, int, int, int, int, int, int, int, (float, float), [(int, int, int)], OPTIONAL(float, 0)), 'processor': process_parties, 'aggregator': aggregate_parties },
	'party_templates':   { 'parser': (id, str, int, int, int, int, [(int, int, int, OPTIONAL(int, 0))]), 'processor': process_party_templates, 'aggregator': aggregate_party_templates },
	'postfx_params':     { 'parser': (id, int, int, (float, float, float, float), (float, float, float, float), (float, float, float, float)), 'processor': process_postfx_params, 'aggregator': aggregate_postfx_params },
	'presentations':     { 'parser': (id, int, int, [(float, SCRIPT)]), 'processor': process_presentations, 'aggregator': aggregate_presentations },
	'quests':            { 'parser': (id, str, int, str), 'processor': process_quests, 'aggregator': aggregate_quests },
	'scene_props':       { 'parser': (id, int, id, id, [(float, SCRIPT)]), 'processor': process_scene_props, 'aggregator': aggregate_scene_props },
	'scenes':            { 'parser': (id, int, id, id, (float, float), (float, float), float, id, [EXPORT.scn], [EXPORT.trp], OPTIONAL(id, '0')), 'processor': process_scenes, 'aggregator': aggregate_scenes },
	'scripts':           { 'parser': (id, SCRIPT), 'processor': process_scripts, 'aggregator': aggregate_scripts },
	'simple_triggers':   { 'parser': (float, SCRIPT), 'processor': process_simple_triggers, 'aggregator': aggregate_simple_triggers, 'uid': None },
	'skills':            { 'parser': (id, str, int, int, str), 'processor': process_skills, 'aggregator': aggregate_simple },
	'skins':             { 'parser': (id, int, id, id, id, id, [(int, int, float, float, str)], [id], [id], [id], [id], [(id, int, [id], [int])], [(int, int)], id, float, int, int, OPTIONAL([(float, int, REPEATABLE, (float, int))], []) ), 'processor': process_skins, 'aggregator': aggregate_skins },
	'sounds':            { 'parser': (id, int, [file]), 'processor': process_sounds, 'aggregator': aggregate_sounds },
	'strings':           { 'parser': (id, str), 'processor': process_strings, 'aggregator': aggregate_strings },
	'tableaus':          { 'parser': (id, int, id, int, int, int, int, int, int, SCRIPT), 'processor': process_tableaus, 'aggregator': aggregate_simple },
	'triggers':          { 'parser': TRIGGER, 'processor': process_triggers, 'aggregator': aggregate_triggers, 'uid': None },
	'troops':            { 'parser': (id, str, str, int, int, int, int, [troop_item], AGGREGATE, AGGREGATE, int, int, OPTIONAL(int, 0), OPTIONAL(str, '0'), OPTIONAL(int, 0), OPTIONAL(int, 0)), 'processor': process_troops, 'aggregator': aggregate_troops },
	'item_modifiers':    { 'parser': (id, str, float, float), 'processor': process_item_modifiers, 'aggregator': aggregate_item_modifiers },
	'ui_strings':        { 'parser': (id, str), 'processor': process_ui_strings, 'aggregator': aggregate_ui_strings, 'uid': None },
	'user_hints':        { 'parser': (str,), 'processor': process_user_hints, 'aggregator': aggregate_ui_strings, 'uid': None },
}


def convert_string_id_to_variable(st, default_src = None):
	st = st.lower()
	if st == '': return 0
	if st[0] == '$':
		new_var = EXPORT.g.__getattr__(st[1:])
		if new_var.value is None:
			EXPORT.g.__setattr__(new_var.name, opmask_variable | len(EXPORT.globals_list))
			EXPORT.globals_list.append(new_var.name)
		return new_var
	if st[0] == ':': return EXPORT.l.__getattr__(st[1:])
	try:
		source, name = st.split('_', 1)
		if source == 'str': source = 's'
		globs = get_globals()
		if (source in globs) and isinstance(globs[source], UID): return globs[source].__getattr__(internal_identifier(name))
	except ValueError:
		pass
	# Let's assume our string is actually identifier name and attempt to divine it from there
	try:
		if default_src is not None: return default_src.__getattr__(st)
	except MSException, e:
		raise MSException('illegal string parameter %r: no matching variable or identifier' % st, *e.args)
	raise MSException('illegal string parameter %r: no matching variable or identifier' % st)

# Returns a VARIABLE, performs some operations if it's a quick string
def parse_string_operand(op, qstr_allowed = True):
	if not op: raise MSException('cannot convert an empty string to identifier or qstr')
	if op[0] == '@':
		if not qstr_allowed: raise MSException('"%s" is a quickstring, identifier expected' % op)
		qval = external_string(op[1:])
		try:
			return EXPORT.qstr_vtv[qval]
		except KeyError:
			pass
		max_offset = len(qval)
		offset = 20
		qkey_etalone = qkey = 'qstr_%s' % external_identifier(qval[0:offset], False)
		iterator = 0
		while EXPORT.qstr_ktv.get(qkey, None) not in (None, qval):
			if offset < max_offset:
				newchar = external_identifier(qval[offset], False)
				qkey_etalone = qkey = qkey + newchar
				offset += 1
			else:
				iterator += 1
				qkey = '%s%d' % (qkey_etalone, iterator)
		new_index = len(EXPORT.qstr_seq)
		EXPORT.qstr_seq.append(qkey)
		EXPORT.qstr_ktv[qkey] = qval
		q_name = 'qs%d' % new_index
		setattr(qstrings, q_name, opmask_quick_string | new_index)
		EXPORT.qstr_vtv[qval] = getattr(qstrings, q_name)
		#print 'NEW QSTR', EXPORT.qstr_vtv[qval], qkey, qval
		return EXPORT.qstr_vtv[qval]
	else:
		return convert_string_id_to_variable(op)

def opcode_to_string(opcode):
	result = []
	if opcode & this_or_next: result.append('this_or_next')
	if opcode & neg: result.append('neg')
	opcode = opcode & 0x3FFFFFFF
	for key, value in OPLIST.__dict__.iteritems():
		if value == opcode:
			result.append(key)
			break
	return '|'.join(result)

def trigger_to_string(trigger):
	for key, value in TRLIST.__dict__.iteritems():
		if (key[0:3] == 'ti_') and (value == trigger): return key
	return 'repeat_trigger(%.01f)' % trigger

def parse_variable_from_int(value):
	tag = value >> op_num_value_bits
	if tag == 0: return value
	if tag == tag_register: return getattr(EXPORT.registers, 'reg%d' % (value & 0xFF))
	raise MSException('value %d not convertible to variable' % value)

def handle_list_injections(entity):
	index = 0
	while index < len(entity):
		if isinstance(entity[index], inject):
			EXPORT.injected.add(entity[index].name)
			injection = EXPORT.injections.get(entity[index].name, [])
			entity = entity[0:index] + injection + entity[index+1:]
		else:
			index += 1
	return entity

# Check for things:
#   certain script should be register-safe - WARNING ??? - might be easier with a separate check
#   usage of local variables that might be undeclared - WARNING ???
#   local variables that are declared but never used - NOTICE ???
def parse_module_code(code_block, script_name, check_can_fail = False):
	EXPORT.start_script()
	code_block = handle_list_injections(code_block)
	locals_def = set()
	export = ['']
	total_commands = len(code_block)
	current_depth = 0
	can_fail = False
	for index in xrange(len(code_block)):
		operation = code_block[index]
		is_assign = False
		if type(operation) in (int, long):
			command = [operation, 0]
		else:
			command = [operation[0], len(operation) - 1]
			command.extend(operation[1:])
		# Monitor execution depth
		if command[0] in (try_begin, try_for_range, try_for_range_backwards, try_for_parties, try_for_agents):
			current_depth += 1
		elif command[0] == try_end:
			current_depth -= 1
		# Check for assignment and can_fail operations
		if command[0] in lhs_operations:
			if len(command) < 3:
				raise MSException('operation %s without an operand in %s on line %d' % (opcode_to_string(command[0]), script_name, index + 1))
			if type(command[2]) == str:
				try:
					command[2] = parse_string_operand(command[2], False)
				except MSException, e:
					raise MSException('operation %s cannot assign to operand %r in %s on line %d' % (opcode_to_string(command[0]), command[2], script_name, index + 1), *e.args)
			elif type(command[2]) in (int, long):
				try:
					command[2] = parse_variable_from_int(command[2])
				except MSException, e:
					raise MSException('operation %s cannot assign to operand %r in %s on line %d' % (opcode_to_string(command[0]), command[2], script_name, index + 1), *e.args)
			if isinstance(command[2], VARIABLE):
				if command[2].is_expression:
					raise MSException('operation %s cannot assign to expression %r in %s on line %d' % (opcode_to_string(command[0]), command[2], script_name, index + 1))
				elif command[2].is_static:
					raise MSException('operation %s cannot assign to static identifier %r in %s on line %d' % (opcode_to_string(command[0]), command[2], script_name, index + 1))
			else:
				#raise MSException('operation %s cannot assign to operand %r in %s on line %d' % (opcode_to_string(command[0]), command[2], script_name, index + 1))
				pass # Because fucking MS actually contains fucking assignment of values to 0.
			is_assign = True
		# Make sure that all operands are legit, allocate local variable ids as necessary
		local_tmp_depth = 0
		try:
			for opindex in xrange(len(command)):
				if opindex < 2: continue
				operand = command[opindex]
				if type(operand) == tuple: command[opindex] = operand = operand[0] # BUGFIX for Taleworlds illegal ACHIEVEMENT_* values
				if type(operand) == str:
					try:
						command[opindex] = operand = parse_string_operand(operand)
					except MSException, e:
						raise MSException('failed to parse operand %r for operation %s in %s on line %d' % (operand, opcode_to_string(command[0]), script_name, index+1), *e.args)
				if isinstance(operand, VARIABLE):
					if operand.is_expression:
						#print repr(operand), operand.__dict__
						if operand.is_static: continue
						#raise MSException('failed to parse operand %r for operation %s in %s on %d\ndynamic code generation not supported yet' % (operand, opcode_to_string(command[0]), script_name, index+1))
						tmp_local = opmask_local_variable | EXPORT.get_local_tmp_id(script_name, local_tmp_depth)
						local_tmp_depth += 1
						extra_commands, operations = operand(script_name, tmp_local, local_tmp_depth)
						#print extra_commands
						#print operations
						#print (' %d' * len(operations)) % tuple(operations)
						command[opindex] = operand = tmp_local
						export.append((' %d' * len(operations)) % tuple(operations))
						total_commands += extra_commands
					elif operand.module == EXPORT.l:
						if (operand.name not in locals_def) and (not(is_assign) or (opindex > 2)):
							EXPORT.errors.append('unassigned local variable %r used by operation %s in %s on line %d' % (operand, opcode_to_string(command[0]), script_name, index + 1))
						operand.value = opmask_local_variable | EXPORT.get_local_id(script_name, operand.name)
		except MSException, e:
			raise MSException('command %r compilation fails in %s on line %d' % (command, script_name, index + 1), *e.args)
		# Identify can_fail scripts
		can_fail |= (current_depth < 1) and (((command[0] & 0x3FFFFFFF) in can_fail_operations) or ((command[0] == call_script) and isinstance(command[1], VARIABLE) and (command[1].module == EXPORT.script) and (command[1].name[0:3] == 'cf_')))
		# If command was an assignment, mark the variable as initialized
		if is_assign:
			if type(command[2]) in (int, long):
				pass
			elif isinstance(command[2], VARIABLE):
				if command[2].module == EXPORT.g:
					try:
						EXPORT.uninitialized.remove(command[2].name)
					except KeyError:
						pass
				elif command[2].module == EXPORT.l:
					locals_def.add(command[2].name)
			else:
				raise MSException('illegal assignment target %r for operation %s in %s on line %d' % (operation, opcode_to_string(command[0]), script_name, index + 1))
		# Generate command compiled text
		try: export.append((' %d' * len(command)) % tuple(command))
		except Exception, e:
			print repr(operation)
			print repr(command)
			raise
	if current_depth != 0:
		EXPORT.errors.append('try/end operations do not match in %s' % (script_name, ))
	if check_can_fail and can_fail and (script_name[0:3] != 'cf_'):
		EXPORT.warnings.append('%s can fail but it\'s name does not start with "cf_"' % script_name)
	export[0] = '%d' % total_commands
	return ''.join(export)

def compressed_tuple(entity):
	output = []
	for sub in entity:
		if type(sub) == list:
			output.append('list[len=%d]' % len(sub))
		elif type(sub) == tuple:
			output.append('tuple(len=%d)' % len(sub))
		elif type(sub) == dict:
			output.append('dict(len=%d)' % len(sub))
		else:
			output.append(sub)
	return repr(tuple(output))

def check_syntax(entity, parser, uid = 0):
	# Handle injections
	if type(entity) == tuple: entity = list(entity) # To guarantee we can make insertions
	if type(entity) == list: entity = handle_list_injections(entity)
	# Process entity
	if type(parser) == tuple:
		if type(uid) == int:
			try:
				possible_uid = entity[uid]
			except IndexError:
				raise MSException('failed to retrieve identifier at position #%d in %s' % (uid, compressed_tuple(entity)))
			if type(possible_uid) != str:
				raise MSException('%r is not a legal identifier at position #%d in %s' % (possible_uid, uid, compressed_tuple(entity)))
			uid = internal_identifier(possible_uid)
		index = 0
		repeating = None
		output = []
		try:
			for subparser in parser:
				if subparser == SCRIPT:
					if type(entity[index]) != list:
						raise MSException('expected script but found %r at position #%d in %s' % (entity[index], index, compressed_tuple(entity)))
					output.append(entity[index])
					index += 1
				elif subparser == AGGREGATE:
					if type(entity[index]) not in (int, long, AGGREGATE):
						raise MSException('expected aggregate value but found %r at position #%d in %s' % (entity[index], index, compressed_tuple(entity)))
					output.append(entity[index])
					index += 1
				elif subparser == REPEATABLE:
					repeating = []
					output.append(repeating)
				elif type(subparser) == dict:
					try:
						output.append(check_syntax(entity[index], subparser['check'], uid))
						index += 1
					except IndexError:
						output.append(deepcopy(subparser['default']))
					except MSException:
						output.append(deepcopy(subparser['default']))
				else:
					if repeating is None:
						output.append(check_syntax(entity[index], subparser, uid))
						index += 1
					else:
						try:
							while True:
								repeating.append(check_syntax(entity[index], subparser, uid))
								index += 1
						except IndexError:
							break
						except MSException, e:
							raise MSException('incorrect syntax at position #%d in %s' % (index, compressed_tuple(entity)), *e.args)
		except IndexError:
			print format_exc()
			raise MSException('not enough elements (%d total) in entity %s' % (len(entity), compressed_tuple(entity)))
		if index < len(entity):
			EXPORT.errors.append('too many elements (%d parsed out of total %d) in entity %s' % (index, len(entity), compressed_tuple(entity)))
		return output
	if type(parser) == list:
		output = []
		for index in xrange(len(entity)):
			try:
				output.append(check_syntax(entity[index], parser[0], uid))
			except MSException, e:
				raise MSException('failed to parse element #%d' % (index, ), *e.args)
		return output
	if parser == troop_item:
		if type(entity) == list:
			return check_syntax(entity, (int, int), uid)
		else:
			return [check_syntax(entity, int, uid), 0]
	elif parser == int:
		if type(entity) == str: entity = convert_string_id_to_variable(entity)
		if isinstance(entity, VARIABLE):
			if not entity.is_static: raise MSException('value of %r is undefined at compile time' % entity)
		elif type(entity) not in (int, long):
			raise MSException('cannot convert value %r to integer' % (entity, ))
	elif isinstance(parser, UID):
		if type(entity) == str: entity = convert_string_id_to_variable(entity, parser)
		if isinstance(entity, VARIABLE):
			if not entity.is_static: raise MSException('value of %r is undefined at compile time' % entity)
		elif type(entity) not in (int, long):
			raise MSException('cannot convert value %r to integer' % (entity, ))
	elif parser == float:
		if type(entity) == str: entity = convert_string_id_to_variable(entity)
		if isinstance(entity, VARIABLE):
			if not entity.is_static: raise MSException('value of %r is undefined at compile time' % entity)
		elif type(entity) not in (int, long, float):
			raise MSException('cannot convert value %r to float' % (entity, ))
	elif parser == str:
		if entity == 0: entity = '0' # DIRTY HACK
		elif type(entity) != str:
			raise MSException('value %r must be a string' % (entity, ))
	elif parser == id:
		# TODO: identifier validity check
		if (type(entity) != str) and (entity not in set([0])): raise MSException('value %r is not a valid identifier' % (entity, ))
	elif parser == file:
		# TODO: filename validity check
		if type(entity) != str: raise MSException('value %r is not a valid filename' % (entity, ))
	elif type(parser) == str:
		if entity != parser: raise MSException('value %r must always be a string constant %r' % (entity, parser))
	else:
		raise MSException('unknown validator type %r' % (parser, ))
	return entity

anim = EXPORT.anim
fac = EXPORT.fac
ip = EXPORT.ip
itm = EXPORT.itm
icon = EXPORT.icon
mnu = EXPORT.mnu
mesh = EXPORT.mesh
mt = EXPORT.mt
track = EXPORT.track
psys = EXPORT.psys
p = EXPORT.p
pt = EXPORT.pt
pfx = EXPORT.pfx
prsnt = EXPORT.prsnt
qst = EXPORT.qst
spr = EXPORT.spr
scn = EXPORT.scn
script = EXPORT.script
skl = EXPORT.skl
snd = EXPORT.snd
tableau = EXPORT.tableau
trp = EXPORT.trp

s = EXPORT.s

l = EXPORT.l
g = EXPORT.g
registers = EXPORT.registers
qstrings = EXPORT.qstrings
imod = EXPORT.imod
imodbit = EXPORT.imodbit

scn.none = 0
scn.exit = 100000

REQUIRED_UIDS = { 'anim': EXPORT.anim, 'fac': EXPORT.fac, 'ip': EXPORT.ip, 'itm': EXPORT.itm, 'icon': EXPORT.icon, 'mnu': EXPORT.mnu, 'mesh': EXPORT.mesh, 'mt': EXPORT.mt, 'track': EXPORT.track, 'psys': EXPORT.psys, 'p': EXPORT.p, 'pt': EXPORT.pt, 'pfx': EXPORT.pfx, 'prsnt': EXPORT.prsnt, 'qst': EXPORT.qst, 'spr': EXPORT.spr, 'scn': EXPORT.scn, 'script': EXPORT.script, 'skl': EXPORT.skl, 'snd': EXPORT.snd, 's': EXPORT.s, 'tableau': EXPORT.tableau, 'trp': EXPORT.trp }
EXPORT.initialized = True

if headers_package:
	from headers import *
	import headers.header_operations as OPLIST
	import headers.header_triggers as TRLIST
else:
	from header_ground_types import *
	from header_item_modifiers import *
	from header_mission_types import *
	from header_terrain_types import *
	from header_operations import *
	from header_animations import *
	from header_dialogs import *
	from header_factions import *
	from header_game_menus import *
	from header_items import *
	from header_map_icons import *
	from header_meshes import *
	from header_mission_templates import *
	from header_music import *
	from header_particle_systems import *
	from header_parties import *
	from header_postfx import *
	from header_presentations import *
	from header_quests import *
	from header_scene_props import *
	from header_scenes import *
	from header_skills import *
	from header_skins import *
	from header_sounds import *
	from header_strings import *
	from header_tableau_materials import *
	from header_triggers import *
	from header_troops import *
	import header_operations as OPLIST
	import header_triggers as TRLIST

from module_constants import *

# OVERRIDING SOME VALUES FROM MODULE SYSTEM HEADERS

def reg(index):
	return getattr(registers, 'reg%d' % index)
def pos(index):
	return getattr(registers, 'pos%d' % index)
for index in xrange(100):
	setattr(registers, 'reg%d' % index, opmask_register|index)
	setattr(registers, 'pos%d' % index, index)
	globals()['reg%d' % index] = reg(index)
	globals()['pos%d' % index] = pos(index)

def SKILLS(**argd):
	result = 0x000000000000000000000000000000000000000000
	for skill_name, value in argd.iteritems():
		result |= (value & 0xF) << (EXPORT.skl.__getattr__(skill_name) << 2)
	return result

def weight(x): return AGGREGATE([('weight', 0.01 * int(x * 100 + 0.5))]) # Allow weights > 63 kg and weight precision up to 0.01 kg (Warband however only displays up to 0.1 kg).
def head_armor(x): return AGGREGATE([('head', x)]) # Allow armor values > 255
def body_armor(x): return AGGREGATE([('body', x)]) # Allow armor values > 255
def leg_armor(x): return AGGREGATE([('leg', x)]) # Allow armor values > 255
def difficulty(x): return AGGREGATE([('diff', x)])
def hit_points(x): return AGGREGATE([('hp', x)]) # Prevent swing damage value overflow into hit points
def spd_rtng(x): return AGGREGATE([('speed', x)])
def shoot_speed(x): return AGGREGATE([('msspd', x)])
def horse_scale(x): return AGGREGATE([('size', x)])
def weapon_length(x): return AGGREGATE([('size', x)])
def shield_width(x): return AGGREGATE([('size', x)])
def shield_height(x): return AGGREGATE([('msspd', x)])
def max_ammo(x): return AGGREGATE([('qty', x)]) # Enable quantity > 255
def swing_damage(damage,damage_type): return AGGREGATE([('swing', (damage_type << iwf_damage_type_bits)|(damage & ibf_armor_mask))]) # Damage is still limited to 255
def thrust_damage(damage,damage_type): return AGGREGATE([('thrust', (damage_type << iwf_damage_type_bits)|(damage & ibf_armor_mask))]) # Damage is still limited to 255
def horse_speed(x): return AGGREGATE([('msspd', x)])
def horse_maneuver(x): return AGGREGATE([('speed', x)])
def horse_charge(x): return thrust_damage(x, 0)
def food_quality(x): return AGGREGATE([('head', x)]) # DEPRECATED
def abundance(x): return AGGREGATE([('abundance', x)])
def accuracy(x): return AGGREGATE([('leg', x)])

def unparse_item_aggregate(value):
	return AGGREGATE({
		'weight': get_weight(value),
		'head': get_head_armor(value),
		'body': get_body_armor(value),
		'leg': get_leg_armor(value),
		'diff': get_difficulty(value),
		'hp': get_hit_points(value) & 0x3ff, # patch for Native compiler glitch
		'speed': get_speed_rating(value),
		'msspd': get_missile_speed(value),
		'size': get_weapon_length(value),
		'qty': get_max_ammo(value),
		'swing': get_swing_damage(value),
		'thrust': get_thrust_damage(value),
		'abundance': get_abundance(value),
	})
def unparse_attr_aggregate(value):
	return AGGREGATE({
		'str': value & 0xFF,
		'agi': (value >> 8) & 0xFF,
		'int': (value >> 16) & 0xFF,
		'cha': (value >> 24) & 0xFF,
		'level': (value >> level_bits) & level_mask
	})
def unparse_wp_aggregate(value):
	return AGGREGATE([(i, (value >> (10*i)) & 0x3FF) for i in xrange(num_weapon_proficiencies)])

def ATTR(_str, _agi, _int, _cha, _lvl = 1): return AGGREGATE([('str', _str), ('agi', _agi), ('int', _int), ('cha', _cha), ('level', _lvl)])
for index in xrange(31):
	if index < 3: continue
	for attr in ('str', 'agi', 'int', 'cha'):
		globals()['%s_%d' % (attr, index)] = AGGREGATE({attr:index})
def_attrib = str_5 | agi_5 | int_4 | cha_4
def level(value):
	return AGGREGATE({'level':value})


def upgrade(*argl):
	if not argl: raise MSException('upgrade() called without parameters in %s' % EXPORT.current_module)
	argl = list(argl)
	if type(argl[0]) == list: argl.pop(0) # Catch for old-style use
	if len(argl) < 2: raise MSException('not enough parameters for upgrade%r in %s' % (argl, EXPORT.current_module))
	base = argl.pop(0)
	upg1 = argl.pop(0)
	try: upg2 = argl.pop(0) # Optional
	except: upg2 = 0
	EXPORT.upgrades.append((EXPORT.current_module, base, upg1, upg2))
upgrade2 = upgrade


def generate_skill_constants_for_backwards_compatibility(skills):
	constants = {}
	for index in xrange(len(skills)):
		sid = internal_identifier(skills[index][0])
		limit = min(15, int(skills[index][3]))
		constants['skl_%s' % sid] = index
		for level in xrange(limit):
			if not level: continue
			constants['knows_%s_%d' % (sid, level)] = level << (index << 2)
	globals().update(constants)

if __name__ == '__main__':
	itm.bread = 8
	imod.lordly = 11
	print check_syntax((itm.bread, 0), troop_item, None)
