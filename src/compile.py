import sys
sys.dont_write_bytecode = True
from traceback import format_exc as formatted_exception
from time import time as gettime
from compiler import *
from os.path import split as path_split, exists as path_exists
from os import makedirs

# Ensure we can print colored text on Windows:
import colorama
colorama.init()

export_item_modifiers = True
export_ui_strings = True
export_user_hints = True

time_started = gettime()
time_loaded = time_plugins = time_identifiers = time_syntax = time_compile = time_export = None
successful = True

# Default values, to be possibly overridden by module_info.py
# These paths are identical by default, but may be overridden when developer is still testing his module for savegame compatibility.
# Compiler will read ID-files to learn what previous reference ID allocation was, and try to stick to it whenever possible.
# For as long as the paths differ, modder can tweak his module files and plugins and compile again to enforce savegame-compatibility.
# Once the compilation is successful and compiler reported savegame compatibility without problems, paths can be made identical, or the files from the write-path simply copied over read-path.
read_id_files  = "ID_%s.py" # Where the compiler will look for previous iteration ID-files.
write_id_files = "ID_%s.py" # Where the compiler will write new iteration ID-files.
enforce_savegame_compatibility = True # By default, compiler will attempt to allocate new entities to any fresh gaps or to the end of the list, irrelevant of their positioning
                                      # within the module files. It will also insert dummy records into any gaps that have not been filled. Setting this parameter to false will turn
                                      # off this behavior, losing the savegame compatibility but allowing the modder to get rid of the accumulated junk.

print
print '\x1b[32m*** Lav\'s Experimental Compiler v. 0.5.3 RC1 ***\x1b[0m'
print 'Please report errors, problems and suggestions at \x1b[34mhttp://forums.taleworlds.com/index.php/topic,304190.0.html\x1b[0m'
print

try:

#   +-----------------------------------------------------------------------------------------------
#  /
# +
# |

	print 'Loading module...',

	try:
		# Optional modules
		EXPORT.current_module = 'item_modifiers'
		try:
			from module_item_modifiers import *
		except ImportError:
			from defaults.module_item_modifiers import *
			export_item_modifiers = False
		EXPORT.current_module = 'ui_strings'
		try:
			from module_ui_strings import *
		except ImportError:
			ui_strings = []
			export_ui_strings = False
		EXPORT.current_module = 'user_hints'
		try:
			from module_user_hints import *
		except ImportError:
			user_hints = []
			export_user_hints = False
		# Required modules
		EXPORT.current_module = 'constants'
		from module_constants import *
		EXPORT.current_module = 'skills'
		from module_skills import *
		generate_skill_constants_for_backwards_compatibility(skills)
		EXPORT.current_module = 'animations'
		from module_animations import *
		EXPORT.current_module = 'factions'
		from module_factions import *
		EXPORT.current_module = 'game_menus'
		from module_game_menus import *
		EXPORT.current_module = 'info_pages'
		from module_info_pages import *
		EXPORT.current_module = 'meshes'
		from module_meshes import *
		EXPORT.current_module = 'mission_templates'
		from module_mission_templates import *
		EXPORT.current_module = 'tracks'
		from module_music import *
		EXPORT.current_module = 'particle_systems'
		from module_particle_systems import *
		EXPORT.current_module = 'postfx_params'
		from module_postfx import *
		EXPORT.current_module = 'quests'
		from module_quests import *
		EXPORT.current_module = 'scene_props'
		from module_scene_props import *
		EXPORT.current_module = 'scenes'
		from module_scenes import *
		EXPORT.current_module = 'scripts'
		from module_scripts import *
		EXPORT.current_module = 'simple_triggers'
		from module_simple_triggers import *
		EXPORT.current_module = 'sounds'
		from module_sounds import *
		EXPORT.current_module = 'strings'
		from module_strings import *
		EXPORT.current_module = 'tableaus'
		from module_tableau_materials import *
		EXPORT.current_module = 'triggers'
		from module_triggers import *
		EXPORT.current_module = 'items'
		from module_items import *
		EXPORT.current_module = 'map_icons'
		from module_map_icons import *
		EXPORT.current_module = 'skins'
		from module_skins import *
		EXPORT.current_module = 'presentations'
		from module_presentations import *
		EXPORT.current_module = 'troops'
		from module_troops import *
		EXPORT.current_module = 'party_templates'
		from module_party_templates import *
		EXPORT.current_module = 'parties'
		from module_parties import *
		EXPORT.current_module = 'dialogs'
		from module_dialogs import *
		EXPORT.current_module = 'info'
		from module_info import *
		EXPORT.destination = export_dir.rstrip('/')
		EXPORT.current_module = None
	except Exception, e:
		print 'FAILED.'
		if isinstance(e, MSException):
			print '\x1b[31mMODULE ERROR:\n%s\x1b[0m' % (e.formatted())
		else:
			print '\x1b[31mCOMPILER INTERNAL ERROR:\n%s\x1b[0m' % formatted_exception()
		time_loaded = gettime()
		raise MSException()
	print 'DONE.'
	time_loaded = gettime()

# |
# +
#  \
#   +===============================================================================================
#  /
# +
# |

	print 'Loading plugins...',

	try:
		plugin = '(none)'
		glob = get_globals()
		for plugin in EXPORT.plugins:
			for parser in parsers.iterkeys():
				if hasattr(glob[plugin], parser):
					glob[parser].extend(getattr(glob[plugin], parser))
			injections = getattr(glob[plugin], 'injection', None)
			if injections:
				for inj_name, inj_elements in injections.iteritems():
					EXPORT.injections.setdefault(inj_name, []).extend(inj_elements)
					#EXPORT.warnings.append('Injection: %d elements for `%s` in `%s`' % (len(inj_elements), inj_name, plugin))
		# Check plugin requirements
		prereq_errors = []
		for plugin, required_by in EXPORT.requirements.iteritems():
			if plugin not in EXPORT.plugins:
				prereq_errors.append('Plugin %s not imported but required by %s.' % (plugin, ', '.join(required_by)))
		if prereq_errors:
			raise MSException('\r\n'.join(prereq_errors))
	except Exception, e:
		print 'FAILED.'
		if isinstance(e, MSException):
			print '\x1b[31mPLUGIN IMPORT ERROR:\n%s\x1b[0m' % (e.formatted())
		else:
			print '\x1b[31mPLUGIN %s IMPORT ERROR:\n%s\x1b[0m' % (plugin, formatted_exception())
		time_plugins = gettime()
		raise MSException()
	print 'DONE.'
	time_plugins = gettime()

# |
# +
#  \
#   +===============================================================================================
#  /
# +
# |

	print 'Checking module syntax...',

	try:
		for entity_name, entity_def in parsers.iteritems():
			get_globals()[entity_name] = check_syntax(get_globals()[entity_name], [entity_def['parser']], entity_def.get('uid', 0))
	except Exception, e:
		print 'FAILED.'
		if isinstance(e, MSException):
			print '\x1b[31mMODULE %s SYNTAX ERROR:\n%s\x1b[0m' % (entity_name, e.formatted())
		else:
			print '\x1b[31mCOMPILER INTERNAL ERROR:\n%s\x1b[0m' % formatted_exception()
		time_syntax = gettime()
		raise MSException()
	print 'DONE.'
	time_syntax = gettime()

# |
# +
#  \
#   +===============================================================================================
#  /
# +
# |

	print 'Allocating identifiers...',

	try:
		allocate_global_variables()
		allocate_quick_strings()
		calculate_identifiers(animations, anim)
		calculate_identifiers(factions, fac)
		calculate_identifiers(info_pages, ip)
		calculate_identifiers(item_modifiers, imod, imodbit)
		calculate_identifiers(items, itm)
		calculate_identifiers(map_icons, icon)
		calculate_identifiers(game_menus, mnu)
		calculate_identifiers(meshes, mesh)
		calculate_identifiers(mission_templates, mt)
		calculate_identifiers(tracks, track)
		calculate_identifiers(particle_systems, psys)
		calculate_identifiers(parties, p)
		calculate_identifiers(party_templates, pt)
		calculate_identifiers(postfx_params, pfx)
		calculate_identifiers(presentations, prsnt)
		calculate_identifiers(quests, qst)
		calculate_identifiers(scene_props, spr)
		calculate_identifiers(scenes, scn)
		calculate_identifiers(scripts, script)
		calculate_identifiers(skills, skl)
		calculate_identifiers(sounds, snd)
		calculate_identifiers(strings, s)
		calculate_identifiers(tableaus, tableau)
		calculate_identifiers(troops, trp)
		undefined = undefined_identifiers()
		if undefined: raise MSException('undeclared identifiers found in module source:\n * %s' % ('\n * '.join(['%s (referenced by \'%s\')' % (name, '\', \''.join(refs)) for name, refs in undefined])))
	except Exception, e:
		print 'FAILED.'
		if isinstance(e, MSException):
			print '\x1b[31mMODULE ERROR:\n%s\x1b[0m' % e.formatted()
		else:
			print '\x1b[31mCOMPILER INTERNAL ERROR:\n%s\x1b[0m' % formatted_exception()
		time_identifiers = gettime()
		raise MSException()
	print 'DONE.'
	time_identifiers = gettime()

# |
# +
#  \
#   +===============================================================================================
#  /
# +
# |

	print 'Compiling module...',

	try:
		stage = 0
		# Pre-processing (note that all entity-level injections are already done but script-level injections are not).
		glob = get_globals()
		preprocess_entities_internal(glob)
		for plugin in EXPORT.plugins:
			processor = getattr(glob[plugin], 'preprocess_entities', None)
			if processor:
				try: processor(glob)
				except Exception, e: raise MSException('Error in %r pre-processor script.' % plugin, formatted_exception())
		# Compiling...
		stage = 1
		for entity_name, entity_def in parsers.iteritems():
			stage = 1
			entities = get_globals()[entity_name]
			stage = 2
			for index in xrange(len(entities)):
				entities[index] = entity_def['processor'](entities[index], index)
			stage = 3
			setattr(EXPORT, entity_name, entity_def['aggregator'](entities))
		# Post-processing (plugins are NOT allowed to do anything here as we are dealing with already compiled code)
		stage = 4
		postprocess_entities()
	except Exception, e:
		print 'FAILED.'
		if isinstance(e, MSException):
			if stage == 0:
				print '\x1b[31mPLUGIN %s PREPROCESSOR ERROR:\n%s\x1b[0m' % (plugin, e.formatted())
			elif stage == 2:
				print '\x1b[31mMODULE %s ENTITY #%d COMPILATION ERROR:\n%s\x1b[0m' % (entity_name, index, e.formatted())
			elif stage == 3:
				print '\x1b[31mMODULE %s AGGREGATOR ERROR:\n%s\x1b[0m' % (entity_name, e.formatted())
			elif stage == 4:
				print '\x1b[31mMODULE POSTPROCESSOR ERROR:\n%s\x1b[0m' % (e.formatted())
		else:
			print '\x1b[31mCOMPILER INTERNAL ERROR:\n%s\x1b[0m' % formatted_exception()
		time_compile = gettime()
		raise MSException()
	print 'DONE.'
	time_compile = gettime()

# |
# +
#  \
#   +===============================================================================================
#  /
# +
# |

	print 'Exporting module...',

	export = {
		'animations': 'actions.txt',
		'dialogs': 'conversation.txt',
		'dialog_states': 'dialog_states.txt',
		'factions': 'factions.txt',
		'game_menus': 'menus.txt',
		'info_pages': 'info_pages.txt',
		'items': 'item_kinds1.txt',
		'map_icons': 'map_icons.txt',
		'meshes': 'meshes.txt',
		'mission_templates': 'mission_templates.txt',
		'tracks': 'music.txt',
		'particle_systems': 'particle_systems.txt',
		'parties': 'parties.txt',
		'party_templates': 'party_templates.txt',
		'postfx_params': 'postfx.txt',
		'presentations': 'presentations.txt',
		'quests': 'quests.txt',
		'scene_props': 'scene_props.txt',
		'scenes': 'scenes.txt',
		'scripts': 'scripts.txt',
		'simple_triggers': 'simple_triggers.txt',
		'skills': 'skills.txt',
		'skins': 'skins.txt',
		'sounds': 'sounds.txt',
		'strings': 'strings.txt',
		'tableaus': 'tableau_materials.txt',
		'triggers': 'triggers.txt',
		'troops': 'troops.txt',
		'variables': 'variables.txt',
		'quick_strings': 'quick_strings.txt',
	}
	if export_item_modifiers: export['item_modifiers'] = 'Data/item_modifiers.txt'
	if export_ui_strings: export['ui_strings'] = 'Languages/en/ui.csv'
	if export_user_hints: export['user_hints'] = 'Languages/en/hints.csv'

	try:
		for entity_name, filename in export.iteritems():
			contents = getattr(EXPORT, entity_name)
			if contents is None:
				#print 'Module %s has no changes, skipping export.' % entity_name
				continue
			#print 'Exporting module %s...' % entity_name
			filename = path_split(filename.replace('\\', '/'))
			folder = ('%s/%s' % (EXPORT.destination, filename[0])) if filename[0] else EXPORT.destination
			if filename[0] and not(path_exists(folder)): makedirs(folder)
			with open('%s/%s' % (folder, filename[1]), 'w+b') as f: f.write(contents)
	except Exception, e:
		print 'FAILED.'
		print '\x1b[31mCOMPILER INTERNAL ERROR WHILE EXPORTING %s:\n%s\x1b[0m' % (entity_name, formatted_exception())
		time_export = gettime()
		raise MSException()

	if write_id_files is not None:
		export = {
			'animations': (EXPORT.anim, 'anim_'),
			'factions': (EXPORT.fac, 'fac_'),
			'info_pages': (EXPORT.ip, 'ip_'),
			'items': (EXPORT.itm, 'itm_'),
			'map_icons': (EXPORT.icon, 'icon_'),
			'menus': (EXPORT.mnu, 'menu_'),
			'meshes': (EXPORT.mesh, 'mesh_'),
			'mission_templates': (EXPORT.mt, 'mst_'),
			'music': (EXPORT.track, 'track_'),
			'particle_systems': (EXPORT.psys, 'psys_'),
			'parties': (EXPORT.p, 'p_'),
			'party_templates': (EXPORT.pt, 'pt_'),
			'postfx_params': (EXPORT.pfx, 'pfx_'),
			'presentations': (EXPORT.prsnt, 'prsnt_'),
			'quests': (EXPORT.qst, 'qst_'),
			'scene_props': (EXPORT.spr, 'spr_'),
			'scenes': (EXPORT.scn, 'scn_'),
			'scripts': (EXPORT.script, 'script_'),
			'skills': (EXPORT.skl, 'skl_'),
			'sounds': (EXPORT.snd, 'snd_'),
			'strings': (EXPORT.s, 'str_'),
			'tableau_materials': (EXPORT.tableau, 'tableau_'),
			'troops': (EXPORT.trp, 'trp_'),
		}
		try:
			for entity_name, (entity, prefix) in export.iteritems():
				contents = '\n'.join([('%s%s = %d' % (prefix, key, int(variable & 0xFFFFFFFF))) for key, variable in entity[0].iteritems()])
				with open(write_id_files % entity_name, 'w+b') as f: f.write(contents)
		except Exception, e:
			print 'FAILED.'
			print '\x1b[31mCOMPILER INTERNAL ERROR WHILE EXPORTING %s:\n%s\x1b[0m' % (write_id_files % entity_name, formatted_exception())
			time_export = gettime()
			raise MSException()

	print 'DONE.'
	time_export = gettime()

# |
# +
#  \
#   +-----------------------------------------------------------------------------------------------


except MSException:
	successful = False

print
if successful: print 'COMPILATION COMPLETE.'
else: print 'COMPILATION CANCELLED.'
print
if time_loaded: print '%.03f sec spent to load module data.' % (time_loaded - time_started)
if time_plugins: print '%.03f sec spent to load plugins.' % (time_plugins - time_loaded)
if time_syntax: print '%.03f sec spent to check module syntax.' % (time_syntax - time_plugins)
if time_identifiers: print '%.03f sec spent to allocate identifiers.' % (time_identifiers - time_syntax)
if time_compile: print '%.03f sec spent to compile module.' % (time_compile - time_identifiers)
if time_export: print '%.03f sec spent to export module.' % (time_export - time_compile)
print '%.03f sec total time spent.' % (gettime() - time_started)
print
if EXPORT.errors:
	print 'The following errors were generated during compilation:\x1b[31m'
	print '\n'.join(EXPORT.errors)
	print '\x1b[0m'
if EXPORT.warnings:
	print '%d warnings were generated during compilation.' % len(EXPORT.warnings)
	reply = raw_input('Display warnings? [Y]es, [n]o >')
	if not(reply) or reply[0].lower() in ('y',):
		print '\x1b[33m%s\x1b[0m' % ('\n'.join(EXPORT.warnings))
		raw_input('Press enter to finish >')
else:
	raw_input('Press enter to finish >')
