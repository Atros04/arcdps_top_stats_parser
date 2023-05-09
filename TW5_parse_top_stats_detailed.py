#!/usr/bin/env python3

#    parse_top_stats_detailed.py outputs detailed top stats in arcdps logs as parsed by Elite Insights.
#    Copyright (C) 2021 Freya Fleckenstein
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import argparse
import datetime
import os.path
from os import listdir
import sys
import xml.etree.ElementTree as ET
from enum import Enum
import importlib
import xlwt

from collections import OrderedDict
from TW5_parse_top_stats_tools import *

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='This reads a set of arcdps reports in xml format and generates top stats.')
	parser.add_argument('input_directory', help='Directory containing .xml or .json files from arcdps reports')
	parser.add_argument('-o', '--output', dest="output_filename", help="Text file to write the computed top stats")
	#parser.add_argument('-f', '--input_filetype', dest="filetype", help="filetype of input files. Currently supports json and xml, defaults to json.", default="json")
	parser.add_argument('-x', '--xls_output', dest="xls_output_filename", help="xls file to write the computed top stats")    
	parser.add_argument('-j', '--json_output', dest="json_output_filename", help="json file to write the computed top stats to")    
	parser.add_argument('-l', '--log_file', dest="log_file", help="Logging file with all the output")
	parser.add_argument('-c', '--config_file', dest="config_file", help="Config file with all the settings", default="TW5_parser_config_detailed")
	parser.add_argument('-a', '--anonymized', dest="anonymize", help="Create an anonymized version of the top stats. All account and character names will be replaced.", default=False, action='store_true')
	args = parser.parse_args()

	if not os.path.isdir(args.input_directory):
		print("Directory ",args.input_directory," is not a directory or does not exist!")
		sys.exit()
	if args.output_filename is None:
		args.output_filename = args.input_directory+"/TW5_top_stats_detailed.tid"
	if args.xls_output_filename is None:
		args.xls_output_filename = args.input_directory+"/TW5_top_stats_detailed.xls"
	if args.json_output_filename is None:
		args.json_output_filename = args.input_directory+"/TW5_top_stats_detailed.json"                
	if args.log_file is None:
		args.log_file = args.input_directory+"/log_detailed.txt"

	output = open(args.output_filename, "w",encoding="utf-8")
	log = open(args.log_file, "w")

	parser_config = importlib.import_module("parser_configs."+args.config_file , package=None) 
	
	config = fill_config(parser_config)

	print_string = "Using input directory "+args.input_directory+", writing output to "+args.output_filename+" and log to "+args.log_file
	print(print_string)
	print_string = "Considering fights with at least "+str(config.min_allied_players)+" allied players and at least "+str(config.min_enemy_players)+" enemies that took longer than "+str(config.min_fight_duration)+" s."
	myprint(log, print_string)

	players, fights, found_healing, found_barrier, squad_comp, squad_offensive, squad_Control, enemy_Control, enemy_Control_Player, downed_Healing, uptime_Table, stacking_uptime_Table, auras_TableOut, Death_OnTag, Attendance, DPS_List, CPS_List, SPS_List, HPS_List, DPSStats = collect_stat_data(args, config, log, args.anonymize)    

	# create xls file if it doesn't exist
	book = xlwt.Workbook(encoding="utf-8")
	book.add_sheet("fights overview")
	book.save(args.xls_output_filename)

	
	#Create Tid file header to support drag and drop onto html page
	myDate = datetime.datetime.now()

	myprint(output, 'created: '+myDate.strftime("%Y%m%d%H%M%S"))
	myprint(output, 'modified: '+myDate.strftime("%Y%m%d%H%M%S"))
	myprint(output, 'creator: '+config.summary_creator)
	myprint(output, 'caption: '+myDate.strftime("%Y%m%d")+'-WvW-Log-Review')
	myprint(output, 'tags: Logs [['+myDate.strftime("%Y")+'-'+myDate.strftime("%m")+' Log Reviews]]')
	myprint(output, 'title: '+myDate.strftime("%Y%m%d")+'-WvW-Log-Review\n')
	#End Tid file header

	#JEL-Tweaked to output TW5 formatting (https://drevarr.github.io/FluxCapacity.html)
	print_string = "__''"+config.summary_title+"''__\n"
	myprint(output, print_string)

	# print overall stats
	overall_squad_stats = get_overall_squad_stats(fights, config)
	overall_raid_stats = get_overall_raid_stats(fights)
	total_fight_duration = print_total_squad_stats(fights, overall_squad_stats, overall_raid_stats, found_healing, found_barrier, config, output)

	include_comp_and_review = config.include_comp_and_review

	large_items = [
		'<$button setTitle="$:/state/curTab" setTo="Squad Composition" selectedClass="" class="btn btn-sm btn-dark" style=""> Squad Composition </$button>',
		'<$button setTitle="$:/state/curTab" setTo="Fight Review" selectedClass="" class="btn btn-sm btn-dark" style=""> Fight Review </$button>'
	] if include_comp_and_review else []

	#Start nav_bar_menu for TW5
	MenuTabs = ['General', 'Offensive', 'Defensive', 'Support', 'Boons & Buffs', 'Dashboard']

	SubMenuTabs = {
	'General': ['Overview', 'Squad Composition', 'Fight Review', 'Spike Damage', 'Attendance', 'Support', 'Distance to Tag', 'Death_OnTag'],
	'Offensive': ['Offensive Stats', 'Down Contribution', 'Enemies Downed', 'Enemies Killed', 'Damage', 'Power Damage', 'Condi Damage', 'DPSStats', 'Burst Damage', 'Damage with Buffs', 'Control Effects - Out', 'Weapon Swaps'],
	'Defensive': ['Defensive Stats', 'Control Effects - In'],
	'Support': ['Healing', 'Barrier', 'Condition Cleanses', 'Duration of Conditions Cleansed', 'Boon Strips', 'Duration of Boons Stripped', 'Illusion of Life', 'Resurrect', 'Downed_Healing', 'Stealth', 'Hide in Shadows', 'FBPages', 'Outgoing Healing'],
	'Boons & Buffs': ['Stability', 'Protection', 'Aegis', 'Might', 'Fury', 'Resistance', 'Resolution', 'Quickness', 'Swiftness', 'Superspeed', 'Alacrity', 'Vigor', 'Regeneration', 'Auras - Out', 'Personal Buffs', 'Skill Casts', 'Buff Uptime', 'Stacking Buffs'],
	'Dashboard': ["Dashboard"]
		}

	alertColors = ["primary", "danger", "warning", "success", "info", "light"]

	excludeForMonthly = ['Squad Composition','Fight Review', 'Spike Damage', 'Outgoing Healing']

	for item in MenuTabs:
		myprint(output, '<$button class="btn btn-sm btn-dark"> <$action-setfield $tiddler="$:/state/MenuTab" $field="text" $value="'+item+'"/> <$action-setfield $tiddler="$:/state/curTab" $field="text" $value="'+SubMenuTabs[item][0]+'"/> '+item+' </$button>')
	
	for item in MenuTabs:
		myprint(output, '<$reveal type="match" state="$:/state/MenuTab" text="'+item+'">')
		myprint(output, '\n')
		myprint(output, '<<alert-leftbar '+alertColors[MenuTabs.index(item)]+' "'+item+'" width:60%, class:"font-weight-bold">>')
		myprint(output, '\n')
		myprint(output, '---')
		for tab in SubMenuTabs[item]:
			if not include_comp_and_review and tab in excludeForMonthly:
				continue
			myprint(output, '<$button setTitle="$:/state/curTab" setTo="'+tab+'" class="btn btn-sm btn-dark"> '+tab+' </$button>')
		myprint(output, '\n')
		myprint(output, '</$reveal>')
		myprint(output, '\n')			

	#End nav_bar_menu for TW5

	#Overview reveal
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Overview">')
	myprint(output, '\n<<alert dark "OVERVIEW" width:60%>>\n')
	myprint(output, '<div style="overflow-x:auto;">\n\n')

	print_fights_overview(fights, overall_squad_stats, overall_raid_stats, config, output)

	#End reveal
	myprint(output, '\n\n</div>\n\n')
	myprint(output, '</$reveal>')

	write_fights_overview_xls(fights, overall_squad_stats, overall_raid_stats, config, args.xls_output_filename)
	
	#Move Squad Composition and Spike Damage here so it is first under the fight summaries

	#Squad Spike Damage
	if include_comp_and_review:
		myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Spike Damage">\n')    
		myprint(output, '\n<<alert dark "SPIKE DAMAGE" width:60%>>\n')
		myprint(output, '\n---\n')    
		myprint(output, '<div style="overflow-x:auto;">\n\n')

		output_string = "\nSquad Damage output by second (Mouse Scroll to zoom in/out at location)\n"
			
		myprint(output, output_string)

		myprint(output, '<$echarts $text={{'+myDate.strftime("%Y%m%d%H%M")+'_spike_damage_heatmap_ChartData}} $height="800px" $theme="dark"/>')

		#end reveal
		myprint(output, '\n\n</div>\n\n')
		myprint(output, "</$reveal>\n")     

	# end Squad Spike Damage

	#Outgoing Healing and Barrier by Target
	if include_comp_and_review:
		myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Outgoing Healing">\n')    
		myprint(output, '\n<<alert dark "Outgoing Healing/Barrier by Target" width:60%>>\n')
		myprint(output, '\n---\n')    
		myprint(output, '<div style="overflow-x:auto;">\n\n')		

		for name in OutgoingHealing:
			myprint(output, '<$button setTitle="$:/state/outgoingHealing" setTo="'+name+'_'+OutgoingHealing[name]['Prof']+'" selectedClass="" class="btn btn-sm btn-dark" style=""> '+name+'{{'+OutgoingHealing[name]['Prof']+'}} </$button>')

		for name in OutgoingHealing:
			myprint(output, '<$reveal type="match" state="$:/state/outgoingHealing" text="'+name+'_'+OutgoingHealing[name]['Prof']+'">')
			myprint(output, '<div style="overflow-x:auto;">\n\n')
			myprint(output, "\n|Healer Name | Party|h")
			myprint (output, "|"+name+" | "+str(OutgoingHealing[name]['Group'])+" |")
			myprint(output, "\n\n---\n")
			myprint(output, "|thead-dark table-caption-top sortable|k")
			myprint(output, "|Sortable Table: Click header to sort|c")
			myprint(output, "|!Player Name | !Party | !Healing| !Barrier|h")
			for target in OutgoingHealing[name]['Targets']:
				if OutgoingHealing[name]['Targets'][target]['Healing'] >0 or OutgoingHealing[name]['Targets'][target]['Barrier']:
					myprint(output, "|"+target+" | "+str(OutgoingHealing[name]['Targets'][target]['Group'])+" | "+str(OutgoingHealing[name]['Targets'][target]['Healing'])+"| "+str(OutgoingHealing[name]['Targets'][target]['Barrier'])+"|")    
			myprint(output, '\n\n</div>\n\n')
			myprint(output, '</$reveal>')

		#end reveal
		myprint(output, '\n\n</div>\n\n')
		myprint(output, "</$reveal>\n")   	

	#Personal Buffs
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Personal Buffs">\n')    
	myprint(output, '\n<<alert dark "Personal Buffs Uptime %" width:60%>>\n')	
	myprint(output, '\n---\n')    
	myprint(output, '<div style="overflow-x:auto;">\n\n')

	BP_Header = ""
	Prof_String = ""
	Output_String = ""
	myprint(output, "|thead-dark|k")
	for profession in buffs_personal:
		BP_Header += '<$button set="$:/state/PersonalBuffs" class="btn btn-sm btn-dark" setTo="'+profession+'">{{'+profession+'}}'+profession+'</$button> '

	myprint(output, BP_Header)
	myprint(output, '\n\n---\n\n')

	for profession in buffs_personal:
		Prof_Header = "|{{"+profession+"}}Name | !Active Time|"
		for buff in buffs_personal[profession]['buffList']:
			icon = skill_Dict[str(buff)]['icon']
			tooltip = skill_Dict[str(buff)]['name']
			Prof_Header += '![img width=24 tooltip="'+tooltip+'" ['+icon+']]|'
		myprint(output, '\n<$reveal type="match" state="$:/state/PersonalBuffs" text="'+profession+'">\n')
		myprint(output, "|thead-dark sortable|k")
		myprint(output, Prof_Header+"h")
		for playerName in buffs_personal[profession]['player']:
			buffUptimes="|"+playerName+" "
			playerActiveTime = 0
			#get activeTime from players
			for player in players:
				if player.name == playerName and player.profession == profession:
					playerActiveTime = player.duration_active
			buffUptimes+="| "+str(playerActiveTime)
			for buff in buffs_personal[profession]['buffList']:
				if buff in buffs_personal[profession]['player'][playerName].keys() and playerActiveTime>0:
					buffUptimes+="| "+str(round((buffs_personal[profession]['player'][playerName][buff]/playerActiveTime)*100,2))
				else:
					buffUptimes+="| 0.00"
			myprint(output, buffUptimes+"|")
		myprint(output, "\n</$reveal>\n")

	#end reveal
	myprint(output, '\n\n</div>\n\n')
	myprint(output, "</$reveal>\n")     

	# end Personal Bufffs

	#Skill casts
	all_classes_post = [
		'12836', # Water Blast Combo
		'9284', # Flame Blast
		'9428', # Frost Burst
		'9292', # Lightning Strike
	]
	profession_skills_to_include = {		
		"Tempest": [
			'5492', # Fire Attunement
			'5493', # Water Attunement
			'5494', # Air Attunement
			'5495', # Earth Attunement
			'29706', # Overload Fire
			'29415', # Overload Water
			'29719', # Overload Air
			'29618', # Overload Earth
			'51711', # Transmute Fire
			'51646', # Transmute Frost
			'51662', # Transmute Lightning
			'51684', # Transmute Earth			
			'29535', # 'Wash the Pain Away!'
			'30432', # 'Aftershock!'
			'29948', # 'Flash-Freeze!'
			'30047', # 'Eye of the Storm!'
			'30662', # 'Feel the Burn!'
			'29968', # 'Rebound!'
			'5762', # Renewal of Fire
			'5763', # Renewal of Water
			'5760', # Renewal of Air
			'5761', # Renewal of Earth
		],
		"Weaver": [
			'43470', # Dual Fire Attunement
			'41166', # Dual Water Attunement
			'42264', # Dual Air Attunement
			'44857', # Dual Earth Attunement
			'-7', # Fire Earth Attunement
			'-14', # Earth Fire Attunement
			'-6', # Fire Air Attunement
			'-11', # Air Fire Attunement						
			'5491', # Fireball
			'5548', # Lava Font
			'5679', # Flame Burst
			'5680', # Burning Retreat
			'5501', # Meteor Shower			
			'5550', # Ice Spike
			'5515', # Frozen Ground
			'5551', # Healing Rain
			'5528', # Eruption
			'5683', # Unsteady Ground
			'5553', # Gust
			'5682', # Windborne Speed
			'5671', # Static Field
			'41125', # Plasma Blast
			'43762', # Pyroclastic Blast
			'5507', # Ether Renewal
			'5736', # Firestorm
			'5737', # Lightning Storm
			'5738', # Sandstorm
			'5641', # Arcane Shield
			'15795', # Mist Form
			'5536', # Lightning Flash
			'45746', # Twist of Fate
			'5567', # Conjure Frost Bow
			'5516', # Conjure Fiery Greatsword
		],
		"Catalyst": [
			'5492', # Fire Attunement
			'5493', # Water Attunement
			'5494', # Air Attunement
			'5495', # Earth Attunement			
			'5491', # Fireball
			'5548', # Lava Font
			'5679', # Flame Burst
			'5680', # Burning Retreat
			'5501', # Meteor Shower			
			'5550', # Ice Spike
			'5515', # Frozen Ground
			'5551', # Healing Rain
			'5528', # Eruption
			'5683', # Unsteady Ground			
			'5553', # Gust
			'5682', # Windborne Speed
			'5671', # Static Field
			'5507', # Ether Renewal
			'5736', # Firestorm
			'5737', # Lightning Storm
			'5738', # Sandstorm
			'5641', # Arcane Shield
			'15795', # Mist Form
			'5536', # Lightning Flash
			'62965', # Relentless Fire
			'5567', # Conjure Frost Bow
			'62725', # Elemental Celerity
			'62813', # Deploy Jade Sphere
			'62723', # Deploy Jade Sphere
			'62940', # Deploy Jade Sphere
			'62837', # Deploy Jade Sphere
		],
		"Spellbreaker": [
			'44165', # Full Counter
			'40601', # Earthshaker
			'42494', # Flurry
			'14366', # Savage Leap
			'14393', # Charge
			'14394', # Call of Valor
			'14358', # Hammer Swing
			'14386', # Fierce Blow
			'14482', # Hammer Shock
			'14359', # Staggering Blow
			'14511', # Backbreaker
			'21815', # Defiant Stance
			'43123', # Break Enchantments
			'14408', # Banner of Tactics
			'14412', # Balanced Stance
			'14392', # Endure Pain
			'45333', # Winds of Disenchantment
			'14419', # Battle Standard
			'14268', # Reckless Impact
			'45534', # Loss Aversion
		],
		"Berserker": [
			'29923', # Scorched Earth
			'29852', # Arc Divider
			'30879', # Rupturing Smash
			'29644', # Gun Flame			
			'14545', # Arcing Slice
			'14546', # Arcing Slice
			'14547', # Arcing Slice
			'14375', # Arcing Slice			
			'14520', # Combustive Shot
			'14521', # Combustive Shot
			'14522', # Combustive Shot
			'14506', # Combustive Shot		
			'14512', # Earthshaker
			'14513', # Earthshaker
			'14514', # Earthshaker
			'40601', # Earthshaker		
			'14356', # Greatsword Swing
			'14554', # Hundred Blades
			'14447', # Whirlwind Attack
			'14510', # Bladetrail
			'14446', # Rush
			'14431', # Dual Shot
			'14519', # Fan of Fire
			'14381', # Arcing Arrow
			'14505', # Smoldering Arrow
			'14504', # Pin Down
			'30189', # Blood Reckoning
			'14410', # Signet of Fury
			'14406', # Berserker Stance
			'14412', # Balanced Stance
			'14392', # Endure Pain
			'29613', # Sundering Leap
			'14405', # Banner of Strength
			'14404', # Signet of Might
			'14419', # Battle Standard
			'14355', # Signet of Rage
		],
		"Firebrand": [
			'13594', # Selfless Daring
			'42449', # Chapter 3: Heated Rebuke
			'42898', # Epilogue: Ashes of the Just
			'42008', # Chapter 4: Shining River
			'42925', # Epilogue: Eternal Oasis
			'41836', # Chapter 3: Valiant Bulwark
			'40988', # Chapter 4: Stalwart Stand
			'44455', # Epilogue: Unbroken Lines
			'9122', # Bolt of Wrath
			'9140', # Holy Strike
			'9143', # Symbol of Swiftness
			'9265', # Empower
			'9144', # Line of Warding
			'9109', # True Strike
			'9111', # Symbol of Faith
			'9086', # Protector's Strike
			'9121', # Protector's Strike
			'9087', # Shield of Judgment
			'9091', # Shield of Absorption
			'45047', # Core Cleave
			'40624', # Symbol of Vengeance
			'45402', # Blazing Edge
			'41714', # Mantra of Solace
			'-20', # Restoring Reprieve or Rejunevating Respite
			'9253', # Hallowed Ground
			'9128', # Sanctuary
			'9163', # Signet of Mercy
			'9251', # Wall of Reflection
			'31159', # Purging Flames
			'9247', # Judge's Intervention
			'45460', # Mantra of Lore
			'-21', # Opening Passage or Clarified Conclusion			
			'43357', # Mantra of Liberation
			'-23', # Portent of Freedom or Unhindered Delivery
			'9154', # Renewed Focus
			'29965', # 'Feel My Wrath!'
		],
		"Dragonhunter": [
			'29887', # Spear of Justice
			'33134', # Hunter's Verdict
			'30783', # Wings of Resolve
			'30029', # Shield of Courage			
			'9098', # Orb of Wrath
			'9090', # Symbol of Punishment
			'9099', # Chains of Light
			'9104', # Zealot's Flame
			'9089', # Zealot's Fire
			'9088', # Cleansing Flame			
			'9122', # Bolt of Wrath
			'9140', # Holy Strike
			'9143', # Symbol of Swiftness
			'9265', # Empower
			'9144', # Line of Warding			
			'30471', # Puncture Shot
			'30229', # True Shot
			'29630', # Deflecting Shot
			'29789', # Symbol of Energy
			'30628', # Hunter's Ward			
			'9102', # Shelter
			'30364', # Procession of Blades
			'9168', # Sword of Justice
			'29786', # Test of Faith
			'9163', # Signet of Mercy
			'9093', # Bane Signet			
			'9154', # Renewed Focus
			'30273', # Dragon's Maw
		],
		"Chronomancer": [
			'56930', # Split Second
			'56925', # Split Second
			'56928', # Rewinder
			'56873', # Time Sink
			'10192', # Distortion
			'29830', # Continuum Split
			'10334', # Blurred Frenzy
			'10186', # Temporal Curtain
			'30769', # Echo of Memory
			'29649', # Deja Vu
			'30643', # Tides of Time
			'30305', # Well of Eternity
			'29578', # Mimic
			'10244', # Illusion of Life
			'10203', # Null Field
			'10187', # Veil
			'10302', # Feedback
			'10237', # Mantra of Concentration
			'10238', # Power Break
			'30359', # Gravity Well
			'29519', # Signet of Humility
		],
		"Druid": [
			'31869', # Celestial Avatar
			'31411', # Release Celestial Avatar
			'31710', # Solar Beam
			'31889', # Astral Wisp
			'31535', # Ancestral Grace
			'31700', # Vine Surge
			'31496', # Sublime Conversion
			'31796', # Cosmic Ray
			'32242', # Seed of Life
			'31318', # Lunar Impact
			'31894', # Rejuvenating Tides
			'31503', # Natural Convergence
			'12480', # Splitblade
			'12466', # Ricochet
			'12490', # Winter's Bite
			'12620', # Hunter's Call
			'12621', # Call of the Wild
			'12489', # Healing Spring
			'31914', # 'We Heal As One!'
			'12631', # 'Protect Me!'
			'31819', # Glyph of Rejuvenation
			'31607', # Glyph of Alignment
			'31658', # Glyph of Equality
			'55046', # Glyph of the Stars
			'31867', # Glyph of Rejuvenation
			'31348', # Glyph of Alignment
			'31401', # Glyph of Equality
			'55024', # Glyph of the Stars
		],
		"Herald": [
			'28085', # Legendary Dragon Stance
			'28419', # Legendary Dwarf Stance
			'28134', # Legendary Assassin Stance
			'28494', # Legendary Demon Stance
			'28549', # Hammer Bolt
			'28253', # Coalescence of Ruin
			'27976', # Phase Smash
			'28110', # Drop the Hammer
			'29057', # Preparation Thrust
			'29233', # Chilling Isolation
			'27220', # Facet of Light
			'28379', # Facet of Darkness
			'27014', # Facet of Elements
			'26644', # Facet of Strength
			'27760', # Facet of Chaos			
			'27162', # Elemental Blast
			'28113', # Burst of Strength
			'28075', # Chaotic Release
			'28516', # Inspiring Reinforcement
			'26557', # Vengeful Hammers			
			'27975', # Rite of the Great Dwarf
		],
		"Vindicator": [
			'28419', # Legendary Dwarf Stance
			'28494', # Legendary Demon Stance
			'28134', # Legendary Assassin Stance
			'28195', # Legendary Centaur Stance
			'62749', # Legendary Alliance
			'62757', # Energy Meld
			'62693', # Death Drop
			'62689', # Saint's Shield
			'28549', # Hammer Bolt
			'28253', # Coalescence of Ruin
			'27976', # Phase Smash
			'28110', # Drop the Hammer
			'62913', # Mist Swing
			'62692', # Mist Unleashed
			'62895', # Phantom's Onslaught
			'62713', # Phantom's Onslaught
			'62921', # Imperial Guard
			'62929', # Eternity's Requiem
			'28516', # Inspiring Reinforcement
			'26557', # Vengeful Hammers			
			'27975', # Rite of the Great Dwarf
			'62719', # Selfish Spirit
			'62832', # Nomad's Advance
			'62962', # Scavenger Burst
			'62878', # Reaver's Rage
			'62942', # Spear of Archemorus
			'62680', # Selfless Spirit
			'62702', # Battle Dance
			'62941', # Tree Song
			'62687', # Urn of Saint Viktor
			'62738', # Drop Urn of Saint Viktor
			'28427', # Ventari's Will
			'29310', # Protective Solace
			'29197', # Purifying Essence
			'29114', # Energy Expulsion
		],
		"Scrapper": [
			'59562', # Explosive Entrance
			'29505', # Reconstruction Field
			'30027', # Defense Field
			'30279', # Chemical Field
			'31167', # Spare Capacitor
			'29665', # Bypass Coating			
			'56920', # Function Gyro
			'30501', # Positive Strike
			'30088', # Electro-whirl
			'30665', # Rocket Charge
			'29840', # Shock Shield
			'30713', # Thunderclap
			'30357', # Medic Gyro
			'29921', # Shredder Gyro
			'31248', # Blast Gyro	
			'29739', # Purge Gyro
			'5927', # Flamethrower
			'5928', # Flame Jet
			'5931', # Flame Blast
			'5930', # Air Blast
			'5929', # Napalm
			'5996', # Magnet
			'5868', # Supply Crate
			'30800', # Elite Mortar Kit
			'30371', # Mortar Shot
			'30885', # Poison Gas Shell
			'30307', # Endothermic Shell
			'30121', # Flash Shell
			'30032', # Elixir Shell
		],
		"Scourge": [
			'44946', # Manifest Sand Shade
			'43448', # Sand Cascade
			'44663', # Desert Shroud			
			'10561', # Rending Claws
			'10528', # Ghastly Claws
			'10701', # Unholy Feast
			'55050', # Soul Grasp
			'10555', # Spinal Shivers			
			'10698', # Blood Curse
			'10532', # Grasping Dead
			'10709', # Feast of Corruption
			'51647', # Devouring Darkness
			'10705', # Deathly Swarm
			'10706', # Enfeebling Blood	
			'10596', # Necrotic Grasp
			'19117', # Mark of Blood
			'10605', # Chillblains
			'19116', # Putrid Mark
			'19115', # Reaper's Mark	
			'43148', # Sand Flare			
			'10548', # Consume Conditions
			'10546', # Well of Suffering
			'10545', # Well of Corruption
			'10607', # Well of Darkness
			'10609', # Well of Power
			'40274', # Trail of Anguish
			'42917', # Sand Swell
			'42355', # Ghastly Breach
			'13906', # Lesser Spinal Shivers
		],
		"Reaper": [
			'30792', # Reaper's Shroud
			'29442', # Life Rend
			'29458', # Life Slash
			'30278', # Life Reap
			'30825', # Death's Charge
			'29958', # Infusing Terror
			'29709', # Terrify
			'30504', # Soul Spiral
			'30557', # Executioner's Scythe
			'10561', # Rending Claws
			'10528', # Ghastly Claws
			'10701', # Unholy Feast
			'55050', # Soul Grasp
			'10555', # Spinal Shivers
			'10698', # Blood Curse
			'10532', # Grasping Dead
			'10709', # Feast of Corruption
			'51647', # Devouring Darkness
			'10705', # Deathly Swarm
			'10706', # Enfeebling Blood
			'29705', # Dusk Strike
			'30799', # Fading Twilight
			'29867', # Chilling Scythe
			'30163', # Gravedigger
			'30860', # Death Spiral
			'29855', # Nightfall
			'29740', # Grasping Darkness
			'10596', # Necrotic Grasp
			'19117', # Mark of Blood
			'10605', # Chillblains
			'19116', # Putrid Mark
			'19115', # Reaper's Mark
			'10546', # Well of Suffering
			'10545', # Well of Corruption
			'10607', # Well of Darkness
			'10609', # Well of Power
			'30488', # 'Your Soul Is Mine!'
			'21762', # Signet of Vampirism
			'29666', # 'Nothing Can Save You!'
			'30105', # 'Chilled to the Bone!'
			'10550', # Lich Form
			'10549', # Plaguelands
		],
	}
	
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Skill Casts">\n')    
	myprint(output, '\n!!!Skill casts / minute\n')
	myprint(output, '\n---\n')    
	myprint(output, '<div style="overflow-x:auto;">\n\n')

	BP_Header = ""
	Prof_String = ""
	Output_String = ""
	myprint(output, "|thead-dark|k")
	for profession in profession_skills_to_include:
		has_player_of_profession = False
		for player in players:
			if player.profession != profession:
				continue
			has_player_of_profession = True
			break

		if has_player_of_profession:
			BP_Header += '<$button set="$:/state/SkillUsage" class="btn btn-sm btn-dark" setTo="'+profession+'">{{'+profession+'}}'+profession+'</$button> '

	myprint(output, BP_Header)
	myprint(output, '\n\n---\n\n')

	for profession in profession_skills_to_include:
		skills_to_include = [
			*profession_skills_to_include[profession],
			*all_classes_post,
		]

		Prof_Header = "|{{"+profession+"}}Name | !Active Time|"
		for buff in skills_to_include:
			# We only want to show skil casts if they happened in these logs
			if profession not in profession_skills or buff not in profession_skills[profession]:
				continue

			icon = skill_Dict[buff]['icon']
			tooltip = skill_Dict[buff]['name'].replace('"',"'")
			Prof_Header += '![img width=24 tooltip="'+tooltip+'" ['+icon+']]|'

		myprint(output, '\n<$reveal type="match" state="$:/state/SkillUsage" text="'+profession+'">\n')
		myprint(output, "|thead-dark sortable|k")
		myprint(output, Prof_Header+"h")

		professionMaxActiveTime = 0
		for player in players:
			if player.profession != profession:
				continue

			professionMaxActiveTime = max(professionMaxActiveTime, player.duration_active)

		for player in players:
			if player.profession != profession:
				continue
			
			playerName = player.name
			playerActiveTime = player.duration_active

			if (playerActiveTime * 100) / professionMaxActiveTime < config.min_attendance_percentage_for_top:
				continue

			buffUptimes="|"+playerName+" "
			buffUptimes+="| "+str(playerActiveTime)
			for buff in skills_to_include:
				# We only want to show skil casts if they happened in these logs
				if profession not in profession_skills or buff not in profession_skills[profession]:
					continue

				if buff in player.skill_usage and playerActiveTime > 0:
					buffUptimes+="| "+str(round((60 * player.skill_usage[buff]) / playerActiveTime, 2))
				else:
					buffUptimes+="| 0.00"
			myprint(output, buffUptimes+"|")
		myprint(output, "\n</$reveal>\n")

	#end reveal
	myprint(output, '\n\n</div>\n\n')
	myprint(output, "</$reveal>\n")     

	# end Skill casts

	if include_comp_and_review:
		#Squad Composition Testing
		myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Squad Composition">')    
		myprint(output, '\n<<alert dark "SQUAD COMPOSITION" width:60%>>\n')
		myprint(output, '\n<div class="flex-row">\n    <div class="flex-col-2 border">\n\n')
		sort_order = ['Firebrand', 'Scrapper', 'Spellbreaker', "Herald", "Chronomancer", "Reaper", "Scourge", "Dragonhunter", "Guardian", "Elementalist", "Tempest", "Revenant", "Weaver", "Willbender", "Renegade", "Vindicator", "Warrior", "Berserker", "Bladesworn", "Engineer", "Holosmith", "Mechanist", "Ranger", "Druid", "Soulbeast", "Untamed", "Thief", "Daredevil", "Deadeye", "Specter", "Catalyst", "Mesmer", "Mirage", "Virtuoso", "Necromancer", "Harbinger"]

		myprint(output, '<div style="overflow-x:auto;">\n\n')

		output_string = ""

		for fight in squad_comp:
			output_string1 = "\n|thead-dark|k\n"
			output_string2 = ""
			output_string1 += "|Fight |"
			output_string2 += "|"+str(fight+1)
			for prof in sort_order:
				if prof in squad_comp[fight]:
					output_string1 += " {{"+str(prof)+"}} |"
					output_string2 += " | "+str(squad_comp[fight][prof])
					
			output_string1 += "h"
			output_string2 += " |\n"
			
			myprint(output, output_string1)
			myprint(output, output_string2)
		myprint(output, '\n\n</div>\n\n')
		myprint(output, '\n</div>\n    <div class="flex-col-2 border">\n')
		myprint(output, '\n!!!ENEMY COMPOSITION\n')    
		myprint(output, '<div style="overflow-x:auto;">\n\n')  
		enemy_squad_num = 0
		for fight in fights:
			if fight.skipped:
				enemy_squad_num += 1
				continue
			enemy_squad_num += 1
			output_string1 = "\n|thead-dark|k\n"
			output_string2 = ""
			output_string1 += "|Fight |"
			output_string2 += "|"+str(enemy_squad_num)
			for prof in sort_order:
				if prof in fight.enemy_squad:
					output_string1 += " {{"+str(prof)+"}} |"
					output_string2 += " | "+str(fight.enemy_squad[prof])

			output_string1 += "h"
			output_string2 += " |\n"

			myprint(output, output_string1)
			myprint(output, output_string2)
		myprint(output, '\n\n</div>\n\n')
		myprint(output, '\n</div>\n</div>\n')
		#end reveal
		print_string = "\n</$reveal>\n"
		myprint(output, print_string)     


		# end Squad Composition insert

		#start Fight DPS Review insert
		myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Fight Review">')    
		myprint(output, '\n<<alert dark "Damage Output Review by Fight-#" width:60%>>\n\n')
		FightNum=0
		for fight in fights:
			FightNum = FightNum+1
			if not fight.skipped:
				myprint(output, '<$button setTitle="$:/state/curFight" setTo="Fight-'+str(FightNum)+'" selectedClass="" class="btn btn-sm btn-dark" style=""> Fight-'+str(FightNum)+' </$button>')
		
		myprint(output, '\n---\n')
		
		FightNum = 0
		for fight in fights:
			FightNum = FightNum+1
			if not fight.skipped:
				myprint(output, '<$reveal type="match" state="$:/state/curFight" text="Fight-'+str(FightNum)+'">')
				myprint(output, '\n<div class="flex-row">\n    <div class="flex-col">\n')
				#begin fight summary
				myprint(output, "|thead-dark table-hover|k")
				myprint(output, "|Fight Summary:|<|h")
				myprint(output, '|Squad Members: |'+str(fight.allies)+' |')
				myprint(output, '|Squad Deaths: |'+str(fight.total_stats['deaths'])+' |')
				myprint(output, '|Enemies: |'+str(fight.enemies)+' |')
				myprint(output, '|Enemies Downed: |'+str(fight.downs)+' |')
				myprint(output, '|Enemies Killed: |'+str(fight.kills)+' |')
				myprint(output, '|Fight Duration: |'+str(fight.duration)+' |')
				myprint(output, '|Fight End Time: |'+str(fight.end_time)+' |')
				myprint(output, '</div></div>\n\n')
				#end fight Summary
				myprint(output, '\n<div class="flex-row">\n    <div class="flex-col-1">\n')
				myprint(output, "|table-caption-top|k")
				myprint(output, "|Damage by Squad Player Descending (Top 20)|c")
				myprint(output, "|thead-dark table-hover|k")
				myprint(output, "|!Squad Member | !Damage Output|h")
				#begin squad DPS totals
				sorted_squad_Dps = dict(sorted(fight.squad_Dps.items(), key=lambda x: x[1], reverse=True))
				counter = 0
				for name in sorted_squad_Dps:
					counter +=1
					if counter <=20:
						myprint(output, '|'+name+'|'+my_value(sorted_squad_Dps[name])+'|')
				#end Squad DPS totals
				myprint(output, '\n</div>\n    <div class="flex-col-1">\n')
				myprint(output, "|table-caption-top|k")
				myprint(output, "|Damage by Squad Skill Descending (Top 20)|c")
				myprint(output, "|thead-dark table-hover|k")
				myprint(output, "|!Squad Skill Name | !Damage Output|h")
				#start   Squad Skill Damage totals
				sorted_squad_skill_dmg = dict(sorted(fight.squad_skill_dmg.items(), key=lambda x: x[1], reverse=True))
				counter = 0
				for name in sorted_squad_skill_dmg:
					counter +=1
					if counter <=20:
						myprint(output, '|'+name+'|'+my_value(sorted_squad_skill_dmg[name])+'|')
				#end Squad Skill Damage totals
				myprint(output, '\n</div>\n    <div class="flex-col-1">\n')
				myprint(output, "|table-caption-top|k")
				myprint(output, "|Damage by Enemy Player Descending (Top 20)|c")            
				myprint(output, "|thead-secondary table-hover|k")
				myprint(output, "|!Enemy Player | !Damage Output|h")
				#begin Enemy DPS totals
				sorted_enemy_Dps = dict(sorted(fight.enemy_Dps.items(), key=lambda x: x[1], reverse=True))
				counter = 0
				for name in sorted_enemy_Dps:
					counter +=1
					if counter <=20:
						myprint(output, '|'+name+'|'+my_value(sorted_enemy_Dps[name])+'|')
				#end Enemy DPS totals
				myprint(output, '\n</div>\n    <div class="flex-col-1">\n')
				myprint(output, "|table-caption-top|k")
				myprint(output, "|Damage by Enemy Skill Descending (Top 20)|c")            
				myprint(output, "|thead-secondary table-hover|k")
				myprint(output, "|!Enemy Skill | !Damage Output|h")
				#begin Enemy Skill Damage       
				sorted_enemy_skill_dmg = dict(sorted(fight.enemy_skill_dmg.items(), key=lambda x: x[1], reverse=True))
				counter = 0
				for name in sorted_enemy_skill_dmg:
					counter +=1
					if counter <=20:
						myprint(output, '|'+name+'|'+my_value(sorted_enemy_skill_dmg[name])+'|')
				#end Enemy Skill Damage
				myprint(output, '\n</div>\n</div>\n')
				myprint(output, "</$reveal>\n")
		myprint(output, "</$reveal>\n")

		#end Fight DPS Review insert

	# print top x players for all stats. If less then x
	# players, print all. If x-th place doubled, print all with the
	# same amount of top x achieved.
	num_used_fights = overall_raid_stats['num_used_fights']

	top_total_stat_players = {key: list() for key in config.stats_to_compute}
	top_consistent_stat_players = {key: list() for key in config.stats_to_compute}
	top_average_stat_players = {key: list() for key in config.stats_to_compute}
	top_percentage_stat_players = {key: list() for key in config.stats_to_compute}
	top_late_players = {key: list() for key in config.stats_to_compute}
	top_jack_of_all_trades_players = {key: list() for key in config.stats_to_compute}    
	
	#JEL-Tweaked to output TW5 formatting (https://drevarr.github.io/FluxCapacity.html)

	for stat in config.stats_to_compute:
		if stat not in config.aurasOut_to_compute and stat not in config.defenses_to_compute:
			if (stat == 'heal' and not found_healing) or (stat == 'barrier' and not found_barrier):
				continue
			
			fileDate = myDate

			#JEL-Tweaked to output TW5 output to maintain formatted table and slider (https://drevarr.github.io/FluxCapacity.html)
			myprint(output,'<$reveal type="match" state="$:/state/curTab" text="'+config.stat_names[stat]+'">')
			myprint(output, "\n!!!<<alert dark src:'"+config.stat_names[stat].upper()+"' width:60%>>\n")
			
			if stat == 'dist':
				myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')
				myprint(output, '<div style="overflow-x:auto;">\n\n')
				top_consistent_stat_players[stat] = get_top_players(players, config, stat, StatType.CONSISTENT)
				top_total_stat_players[stat] = get_top_players(players, config, stat, StatType.TOTAL)
				top_average_stat_players[stat] = get_top_players(players, config, stat, StatType.AVERAGE)            
				top_percentage_stat_players[stat],comparison_val = get_and_write_sorted_top_percentage(players, config, num_used_fights, stat, output, StatType.PERCENTAGE, top_consistent_stat_players[stat])
				myprint(output, '\n\n\n\n')
				top_percentage_stat_players[stat],comparison_val = get_top_percentage_players(players, config, stat, StatType.PERCENTAGE, num_used_fights, top_consistent_stat_players[stat], top_total_stat_players[stat], list(), list())
				top_average_stat_players[stat] = get_and_write_sorted_average(players, config, num_used_fights, stat, output)			
				myprint(output, '\n\n</div>\n\n')
				myprint(output, '\n</div>\n    <div class="flex-col border">\n')
				myprint(output, '<div style="overflow-x:auto;">\n\n')
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_'+stat+'_ChartData}} $height="800px" $theme="dark"/>')
				myprint(output, '\n\n</div>\n\n')
				myprint(output, '\n</div>\n</div>\n')
			else:
				myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')
				myprint(output, '<div style="overflow-x:auto;">\n\n')
				if config.player_sorting_stat_type == 'average':
					top_average_stat_players[stat] = get_and_write_sorted_total_by_average(players, config, total_fight_duration, stat, output)
					top_total_stat_players[stat] = get_top_players(players, config, stat, StatType.TOTAL)
				else:
					top_total_stat_players[stat] = get_and_write_sorted_total(players, config, total_fight_duration, stat, output)
					top_average_stat_players[stat] = get_top_players(players, config, stat, StatType.AVERAGE)	
				myprint(output, '\n\n\n\n')
				top_consistent_stat_players[stat] = get_and_write_sorted_top_consistent(players, config, num_used_fights, stat, output)			
				myprint(output, '\n\n</div>\n\n')
				myprint(output, '\n</div>\n    <div class="flex-col border">\n')
				myprint(output, '<div style="overflow-x:auto;">\n\n')
				#top_total_stat_players[stat] = get_and_write_sorted_total(players, config, total_fight_duration, stat, output)
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_'+stat+'_ChartData}} $height="800px" $theme="dark"/>')
				myprint(output, '\n\n</div>\n\n')
				myprint(output, '\n</div>\n</div>\n')
				top_average_stat_players[stat] = get_top_players(players, config, stat, StatType.AVERAGE)
				top_percentage_stat_players[stat],comparison_val = get_top_percentage_players(players, config, stat, StatType.PERCENTAGE, num_used_fights, top_consistent_stat_players[stat], top_total_stat_players[stat], list(), list())
				
				#myprint(output, '<div>')
				#myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_'+stat+'_ChartData}} $height="800px" $theme="dark"/>')
				#myprint(output, '</div>')
			#JEL-Tweaked to output TW5 output to maintain formatted table and slider (https://drevarr.github.io/FluxCapacity.html)
			myprint(output, "</$reveal>\n")

	#print Auras-Out details
	myprint(output,'<$reveal type="match" state="$:/state/curTab" text="Auras - Out">')
	myprint(output, '\n!!!<<alert dark src:"Auras - Out" width:60%>>\n')
	for stat in config.aurasOut_to_compute:
		myprint(output, '<$button setTitle="$:/state/curAuras-Out" setTo="'+config.stat_names[stat]+'" selectedClass="" class="btn btn-sm btn-dark" style="">'+config.stat_names[stat]+' </$button>')

	for stat in config.aurasOut_to_compute:
		myprint(output,'<$reveal type="match" state="$:/state/curAuras-Out" text="'+config.stat_names[stat]+'">')
		myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')
		myprint(output, '<div style="overflow-x:auto;">\n\n')
		if config.player_sorting_stat_type == 'average':
			top_average_stat_players[stat] = get_and_write_sorted_total_by_average(players, config, total_fight_duration, stat, output)
			top_total_stat_players[stat] = get_top_players(players, config, stat, StatType.TOTAL)
		else:
			top_total_stat_players[stat] = get_and_write_sorted_total(players, config, total_fight_duration, stat, output)
			top_average_stat_players[stat] = get_top_players(players, config, stat, StatType.AVERAGE)
		myprint(output, '\n\n')
		top_consistent_stat_players[stat] = get_and_write_sorted_top_consistent(players, config, num_used_fights, stat, output)			
		myprint(output, '\n</div>')
		myprint(output, '\n</div>\n    <div class="flex-col border">\n')
		myprint(output, '<div style="overflow-x:auto;">\n')
		#top_total_stat_players[stat] = get_and_write_sorted_total(players, config, total_fight_duration, stat, output)
		myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_'+stat+'_ChartData}} $height="800px" $theme="dark"/>')
		myprint(output, '\n</div>')
		myprint(output, '\n</div></div>\n')
		top_percentage_stat_players[stat],comparison_val = get_top_percentage_players(players, config, stat, StatType.PERCENTAGE, num_used_fights, top_consistent_stat_players[stat], top_total_stat_players[stat], list(), list())
		myprint(output, "</$reveal>\n")
	myprint(output, "</$reveal>\n")	

	#print Defense details
	myprint(output,'<$reveal type="match" state="$:/state/curTab" text="Defensive Stats">')
	myprint(output, '\n!!!<<alert dark src:"Defensive Stats" width:60%>>\n')
	myprint(output, '<$button setTitle="$:/state/curDefense" setTo="Overview" selectedClass="" class="btn btn-sm btn-dark" style=""> Defensive Overview </$button>')
	for stat in config.defenses_to_compute:
		myprint(output, '<$button setTitle="$:/state/curDefense" setTo="'+config.stat_names[stat]+'" selectedClass="" class="btn btn-sm btn-dark" style="">'+config.stat_names[stat]+' </$button>')

	#Print Overview Table
	DefensiveOverview = ['dmg_taken', 'barrierDamage', 'hitsMissed', 'interupted', 'invulns', 'evades', 'blocks', 'dodges', 'cleansesIn', 'ripsIn', 'downed', 'deaths']
	myprint(output,'<$reveal type="match" state="$:/state/curDefense" text="Overview">')	
	myprint(output, '<div style="overflow-x:auto;">\n\n')
	myprint(output, "|thead-dark table-hover sortable|k")	
	myprint(output, "|!Name |!Profession | !{{Damage Taken}} | !{{BarrierDamage}} | !{{MissedHits}} | !{{Interrupted}} | !{{Invuln}} | !{{Evades}} | !{{Blocks}} | !{{Dodges}} | !{{Condition Cleanses}} | !{{Boon Strips}} | !{{Downed}} | !{{Died}} |h")
	for player in players:
		player_name = player.name
		player_prof = player.profession
		print_string = "|"+player_name+"| {{"+player_prof+"}} "
		for item in DefensiveOverview:
			print_string += "| "+my_value(player.total_stats[item])
		print_string +="|"
		myprint(output, print_string)
	myprint(output, '\n</div>')
	myprint(output, '\n</$reveal>')
	for stat in config.defenses_to_compute:
		myprint(output,'<$reveal type="match" state="$:/state/curDefense" text="'+config.stat_names[stat]+'">')
		myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')
		myprint(output, '<div style="overflow-x:auto;">\n\n')
		if config.player_sorting_stat_type == 'average':
			top_average_stat_players[stat] = get_and_write_sorted_total_by_average(players, config, total_fight_duration, stat, output)
			top_total_stat_players[stat] = get_top_players(players, config, stat, StatType.TOTAL)
		else:
			top_total_stat_players[stat] = get_and_write_sorted_total(players, config, total_fight_duration, stat, output)
			top_average_stat_players[stat] = get_top_players(players, config, stat, StatType.AVERAGE)
		myprint(output, '\n\n')
		top_consistent_stat_players[stat] = get_and_write_sorted_top_consistent(players, config, num_used_fights, stat, output)			
		myprint(output, '\n</div>')
		myprint(output, '\n</div>\n    <div class="flex-col border">\n')
		myprint(output, '<div style="overflow-x:auto;">\n')
		#top_total_stat_players[stat] = get_and_write_sorted_total(players, config, total_fight_duration, stat, output)
		myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_'+stat+'_ChartData}} $height="800px" $theme="dark"/>')
		myprint(output, '\n</div>')
		myprint(output, '\n</div></div>\n')
		top_percentage_stat_players[stat],comparison_val = get_top_percentage_players(players, config, stat, StatType.PERCENTAGE, num_used_fights, top_consistent_stat_players[stat], top_total_stat_players[stat], list(), list())
		myprint(output, "</$reveal>\n")
	myprint(output, "</$reveal>\n")	
	write_to_json(overall_raid_stats, overall_squad_stats, fights, players, top_total_stat_players, top_average_stat_players, top_consistent_stat_players, top_percentage_stat_players, top_late_players, top_jack_of_all_trades_players, squad_offensive, squad_Control, enemy_Control, enemy_Control_Player, downed_Healing, uptime_Table, stacking_uptime_Table, auras_TableOut, Death_OnTag, Attendance, DPS_List, CPS_List, SPS_List, HPS_List, DPSStats, args.json_output_filename)

	#print table of accounts that fielded support characters
	myprint(output,'<$reveal type="match" state="$:/state/curTab" text="Support">')
	myprint(output, '\n<<alert dark "Support Players" width:60%>>\n')
	myprint(output, "\n")
	myprint(output, '<div style="overflow-x:auto;">\n\n')
	# print table header
	print_string = "|thead-dark table-hover sortable|k"    
	myprint(output, print_string)
	print_string = "|!Account |!Name |!Profession | !Fights| !Duration|!Support |!Guild Status |h"
	myprint(output, print_string)    

	for stat in config.stats_to_compute:
		if (stat == 'rips' or stat == 'cleanses' or stat == 'stability' or stat == 'heal'):
			write_support_players(players, top_total_stat_players[stat], stat, output)

	myprint(output, '\n\n</div>\n\n')
	myprint(output, "</$reveal>\n")

	supportCount=0

	#print table of accounts with attendance details
	myprint(output,'<$reveal type="match" state="$:/state/curTab" text="Attendance">')
	myprint(output, '\n<<alert dark "Attendance" width:60%>>\n')
	myprint(output, "\n")
	myprint(output, '<div style="overflow-x:auto;">\n\n')
	# print table header
	print_string = "|thead-dark table-hover sortable|k"    
	myprint(output, print_string)
	print_string = "|!Account |Prof_Name | Role| !Fights| !Duration| !Guild Status|h"
	myprint(output, print_string)    

	for account in Attendance:
		Acct_Fights = Attendance[account]['fights']
		Acct_Duration = Attendance[account]['duration']
		Acct_Guild_Status = Attendance[account]['guildStatus']
		print_string = "|''"+account+"'' | | | ''"+str(Acct_Fights)+"''| ''"+str(Acct_Duration)+"''| ''"+Acct_Guild_Status+"''|h"
		myprint(output, print_string)
		for name in Attendance[account]['names']:
			for prof in Attendance[account]['names'][name]['professions']:
				prof_fights = Attendance[account]['names'][name]['professions'][prof]['fights']
				prof_duration = Attendance[account]['names'][name]['professions'][prof]['duration']
				print_string = "| |{{"+prof.split()[0]+"}}"+name+"  | "+prof.split()[1]+" | "+str(prof_fights)+"| "+str(prof_duration)+"| "+Acct_Guild_Status+"|"
				myprint(output, print_string)

	myprint(output, '\n\n</div>\n\n')
	myprint(output, "</$reveal>\n")

	#start Control Effects Outgoing insert
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Control Effects - Out">')    
	myprint(output, '\n<<alert dark "Outgoing Control Effects generated by the Squad" width:60%>>\n\n')
	Control_Effects = {720: 'Blinded', 721: 'Crippled', 722: 'Chilled', 727: 'Immobile', 742: 'Weakness', 791: 'Fear', 833: 'Daze', 872: 'Stun', 26766: 'Slow', 27705: 'Taunt', 30778: "Hunter's Mark"}
	for C_E in Control_Effects:
		myprint(output, '<$button setTitle="$:/state/curControl-Out" setTo="'+Control_Effects[C_E]+'" selectedClass="" class="btn btn-sm btn-dark" style="">'+Control_Effects[C_E]+' </$button>')
	myprint(output, '<$button setTitle="$:/state/curControl-Out" setTo="MOA Tracking" selectedClass="" class="btn btn-sm btn-dark" style="">MOA Tracking </$button>')
	myprint(output, '\n---\n')
	

	for C_E in Control_Effects:
		key = Control_Effects[C_E]
		if key in squad_Control:
			sorted_squadControl = dict(sorted(squad_Control[key].items(), key=lambda x: x[1], reverse=True))

			i=1
		
			myprint(output, '<$reveal type="match" state="$:/state/curControl-Out" text="'+key+'">\n')
			myprint(output, '\n---\n')
			myprint(output, "|table-caption-top|k")
			myprint(output, "|{{"+key+"}} "+key+" output by Squad Player Descending [TOP 25 Max]|c")
			myprint(output, "|thead-dark table-hover sortable|k")
			myprint(output, "|!Place |!Name | !Profession | !Total| !Average|h")
			
			for name in sorted_squadControl:
				prof = "Not Found"
				fightTime = 99999 
				counter = 0
				for nameIndex in players:
					if nameIndex.name == name:
						prof = nameIndex.profession
						fightTime = nameIndex.duration_fights_present

				if i <=25:
					myprint(output, "| "+str(i)+" |"+name+" | {{"+prof+"}} | "+str(round(sorted_squadControl[name], 4))+"| "+"{:.4f}".format(round(sorted_squadControl[name]/fightTime, 4))+"|")
					i=i+1

			myprint(output, "</$reveal>\n")

			write_control_effects_out_xls(sorted_squadControl, key, players, args.xls_output_filename)


	#Add MOA Tracking Tables
	myprint(output, '<$reveal type="match" state="$:/state/curControl-Out" text="MOA Tracking">\n')
	myprint(output, '\n---\n')
	myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')
	myprint(output, "|table-caption-top|k")
	myprint(output, "|MOA Attempts by Squad Player|c")
	myprint(output, "|!Name | Attempted MOA Casting |h")	
	for name in MOA_Casters:
		myprint(output, "|"+name+" | "+str(MOA_Casters[name]['attempts'])+" |")
	myprint(output, '\n    </div>\n    <div class="flex-col border">\n')
	#MOA Target Table
	myprint(output, "|table-caption-top|k")
	myprint(output, "|Confirmed Missed MOA Attempts by Target|c")
	myprint(output, "|!Name | Missed | Blocked | Invulned |h")	
	for name in MOA_Targets:
		myprint(output, "|"+name+" | "+str(MOA_Targets[name]['missed'])+" | "+str(MOA_Targets[name]['blocked'])+" | "+str(MOA_Targets[name]['invulned'])+" |")
	myprint(output, '\n    </div>\n</div>\n')
	myprint(output, "</$reveal>\n")

	myprint(output, "</$reveal>\n")	
	#end Control Effects Outgoing insert

	#start Control Effects Incoming insert
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Control Effects - In">')    
	myprint(output, '\n<<alert dark "Incoming Control Effects generated by the Enemy" width:60%>>\n\n')
	Control_Effects = {720: 'Blinded', 721: 'Crippled', 722: 'Chilled', 727: 'Immobile', 742: 'Weakness', 791: 'Fear', 833: 'Daze', 872: 'Stun', 26766: 'Slow', 27705: 'Taunt', 30778: "Hunter's Mark"}
	for C_E in Control_Effects:
		myprint(output, '<$button setTitle="$:/state/curControl-In" setTo="'+Control_Effects[C_E]+'" selectedClass="" class="btn btn-sm btn-dark" style="">'+Control_Effects[C_E]+' </$button>')
	
	myprint(output, '\n---\n')
	

	for C_E in Control_Effects:
		key = Control_Effects[C_E]
		if key in enemy_Control:
			sorted_enemyControl = dict(sorted(enemy_Control[key].items(), key=lambda x: x[1], reverse=True))

			i=1
			
			myprint(output, '<$reveal type="match" state="$:/state/curControl-In" text="'+key+'">\n')
			myprint(output, '\n---\n')
			myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')
			myprint(output, "|table-caption-top|k")
			myprint(output, "|{{"+key+"}} "+key+" impacted Squad Player Descending [TOP 25 Max]|c")
			myprint(output, "|thead-dark table-hover sortable|k")
			myprint(output, "|!Place |!Name | !Profession | !Total| !Average|h")
			
			for name in sorted_enemyControl:
				prof = "Not Found"
				fightTime = 99999 
				counter = 0
				for nameIndex in players:
					if nameIndex.name == name:
						prof = nameIndex.profession
						fightTime = nameIndex.duration_fights_present

				if i <=25:
					myprint(output, "| "+str(i)+" |"+name+" | {{"+prof+"}} | "+str(round(sorted_enemyControl[name], 4))+"| "+"{:.4f}".format(round(sorted_enemyControl[name]/fightTime, 4))+"|")
					i=i+1

			#myprint(output, "</$reveal>\n")

			write_control_effects_in_xls(sorted_enemyControl, key, players, args.xls_output_filename)

		if key in enemy_Control_Player:
			sorted_enemyControlPlayer = dict(sorted(enemy_Control_Player[key].items(), key=lambda x: x[1], reverse=True))

			i=1
	
			myprint(output, '\n---\n')
			myprint(output, '\n</div>\n    <div class="flex-col border">\n')
			myprint(output, "|table-caption-top|k")
			myprint(output, "|{{"+key+"}} "+key+" output by Enemy Player Descending [TOP 25 Max]|c")
			myprint(output, "|thead-dark table-hover sortable|k")
			myprint(output, "|!Place |!Name | !Profession | !Total|h")
		
			for name in sorted_enemyControlPlayer:
				prof = name.split(' pl')[0]
				counter = 0

				if i <=25:
					myprint(output, "| "+str(i)+" |"+name+" | {{"+prof+"}} | "+str(round(sorted_enemyControlPlayer[name],4 ))+"|")
					i=i+1

			myprint(output, '\n</div>\n</div>\n')
			myprint(output, "</$reveal>\n")

	myprint(output, "</$reveal>\n")
	#end Control Effects Incoming insert

	#start Buff Uptime Table insert
	uptime_Order = ['stability',  'protection',  'aegis',  'might',  'fury',  'resistance',  'resolution',  'quickness',  'swiftness',  'alacrity',  'vigor',  'regeneration']
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Buff Uptime">')    
	myprint(output, '\n<<alert dark "Total Buff Uptime %" width:60%>>\n\n')
	
	myprint(output, '\n---\n')
	myprint(output, '\n---\n')

	myprint(output, "|table-caption-top|k")
	myprint(output, "|Sortable table - Click header item to sort table |c")
	myprint(output, "|thead-dark table-hover sortable|k")
	myprint(output, "|!Name | !Profession | !Attendance| !{{Stability}}|  !{{Protection}}|  !{{Aegis}}|  !{{Might}}|  !{{Fury}}|  !{{Resistance}}|  !{{Resolution}}|  !{{Quickness}}|  !{{Swiftness}}|  !{{Alacrity}}|  !{{Vigor}}|  !{{Regeneration}}|h")
	for squadDps_prof_name in uptime_Table:
		fightTime = uptime_Table[squadDps_prof_name]['duration']
		name = uptime_Table[squadDps_prof_name]['name']
		prof = uptime_Table[squadDps_prof_name]['prof']

		output_string = "|"+name+" |"
		output_string += " {{"+prof+"}} | "+my_value(round(fightTime))+"|"
		for item in uptime_Order:
			if item in uptime_Table[squadDps_prof_name] and fightTime >0:
				output_string += " "+"{:.4f}".format(round(((uptime_Table[squadDps_prof_name][item]/fightTime)*100), 4))+"|"
			else:
				output_string += " 0.00|"
				


		myprint(output, output_string)

	write_buff_uptimes_in_xls(uptime_Table, players, uptime_Order, args.xls_output_filename)
	myprint(output, "</$reveal>\n")
	#end Buff Uptime Table insert

	max_fightTime = 0
	for squadDps_prof_name in DPSStats:
		max_fightTime = max(DPSStats[squadDps_prof_name]['duration'], max_fightTime)
	
	#start Stacking Buff Uptime Table insert
	stacking_buff_Order = ['might', 'stability']
	max_stacking_buff_fight_time = 0
	for uptime_prof_name in stacking_uptime_Table:
		max_stacking_buff_fight_time = max(stacking_uptime_Table[uptime_prof_name]['duration_might'], max_stacking_buff_fight_time)
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Stacking Buffs">')    
	myprint(output, '\n<<alert dark "Stacking Buffs" width:60%>>\n\n')
	for stacking_buff in stacking_buff_Order:
		myprint(output, '<$button setTitle="$:/state/curStackingBuffs" setTo="'+stacking_buff+'" selectedClass="" class="btn btn-sm btn-dark" style="">'+stacking_buff+'</$button>')
	
	myprint(output, '\n---\n')

	# Might stack table
	myprint(output, '<$reveal type="match" state="$:/state/curStackingBuffs" text="might">\n')
	myprint(output, '\n---\n')
	myprint(output, "|table-caption-top|k")
	myprint(output, "|{{Might}} uptime by stack|c")
	myprint(output, '|thead-dark table-hover sortable|k')
	output_header =  '|!Name | !Class'
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Avg| !1+ %| !5+ %| !10+ %| !15+ %| !20+ %| !25 %'
	output_header += '|h'
	myprint(output, output_header)
	
	might_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_might'] / 1000) or 1
		might_stacks = stacking_uptime_Table[uptime_prof_name]['might']

		if (DPSStats[uptime_prof_name]['duration'] * 100) / max_fightTime < config.min_attendance_percentage_for_top:
			continue

		avg_might = sum(stack_num * might_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		might_sorted_stacking_uptime_Table.append([uptime_prof_name, avg_might])
	might_sorted_stacking_uptime_Table = sorted(might_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	might_sorted_stacking_uptime_Table = list(map(lambda x: x[0], might_sorted_stacking_uptime_Table))
	
	for uptime_prof_name in might_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_might'] / 1000) or 1
		might_stacks = stacking_uptime_Table[uptime_prof_name]['might']

		avg_might = sum(stack_num * might_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		might_uptime = 1.0 - (might_stacks[0] / (fight_time * 1000))
		might_5_uptime = sum(might_stacks[i] for i in range(5,26)) / (fight_time * 1000)
		might_10_uptime = sum(might_stacks[i] for i in range(10,26)) / (fight_time * 1000)
		might_15_uptime = sum(might_stacks[i] for i in range(15,26)) / (fight_time * 1000)
		might_20_uptime = sum(might_stacks[i] for i in range(20,26)) / (fight_time * 1000)
		might_25_uptime = might_stacks[25] / (fight_time * 1000)

		output_string = '|'+name+' |'+' {{'+prof+'}} | '+my_value(round(fight_time))
		output_string += '|'+"{:.2f}".format(avg_might)
		output_string += "| "+"{:.2f}".format(round((might_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_5_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_10_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_15_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_20_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((might_25_uptime * 100), 4))+"%"
		output_string += '|'

		myprint(output, output_string)

	myprint(output, "</$reveal>\n")
	
	# Stability stack table
	myprint(output, '<$reveal type="match" state="$:/state/curStackingBuffs" text="stability">\n')
	myprint(output, '\n---\n')
	myprint(output, "|table-caption-top|k")
	myprint(output, "|{{Stability}} uptime by stack|c")
	myprint(output, '|thead-dark table-hover sortable|k')
	output_header =  '|!Name | !Class'
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Avg| !1+ %| !2+ %| !5+ %'
	output_header += '|h'
	myprint(output, output_header)
	
	stability_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_stability'] / 1000) or 1
		stability_stacks = stacking_uptime_Table[uptime_prof_name]['stability']

		if (DPSStats[uptime_prof_name]['duration'] * 100) / max_fightTime < config.min_attendance_percentage_for_top:
			continue

		avg_stab = sum(stack_num * stability_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		stability_sorted_stacking_uptime_Table.append([uptime_prof_name, avg_stab])
	stability_sorted_stacking_uptime_Table = sorted(stability_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	stability_sorted_stacking_uptime_Table = list(map(lambda x: x[0], stability_sorted_stacking_uptime_Table))
	
	for uptime_prof_name in stability_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_stability'] / 1000) or 1
		stability_stacks = stacking_uptime_Table[uptime_prof_name]['stability']

		avg_stab = sum(stack_num * stability_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		stab_uptime = 1.0 - (stability_stacks[0] / (fight_time * 1000))
		stab_2_uptime = sum(stability_stacks[i] for i in range(2,26)) / (fight_time * 1000)
		stab_5_uptime = sum(stability_stacks[i] for i in range(5,26)) / (fight_time * 1000)

		output_string = '|'+name+' |'+' {{'+prof+'}} | '+my_value(round(fight_time))
		output_string += '|'+"{:.2f}".format(avg_stab)
		output_string += "| "+"{:.2f}".format(round((stab_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((stab_2_uptime * 100), 4))+"%"
		output_string += "| "+"{:.2f}".format(round((stab_5_uptime * 100), 4))+"%"
		output_string += '|'

		myprint(output, output_string)

	myprint(output, "</$reveal>\n")
	myprint(output, "</$reveal>\n")
	
	write_stacking_buff_uptimes_in_xls(stacking_uptime_Table, args.xls_output_filename)
	#end Stacking Buff Uptime Table insert


	#start Stacking Buff Uptime Table insert
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Damage with Buffs">')    
	myprint(output, '\n<<alert dark "Damage with Buffs" width:60%>>\n\n')
	myprint(output, '\n---\n')
	myprint(output, '!!! `Damage with buff %` \n')
	myprint(output, '!!! Percentage of damage done with a buff, similar to uptime %, but based on damage dealt \n')
	myprint(output, '!!! `Damage % - Uptime %` \n')
	myprint(output, '!!! The difference in `damage with buff %` and `uptime %` \n')
	myprint(output, '\n---\n')
	myprint(output, '<$button setTitle="$:/state/curDamageWithBuffs" setTo="might" selectedClass="" class="btn btn-sm btn-dark" style="">might</$button>')
	myprint(output, '<$button setTitle="$:/state/curDamageWithBuffs" setTo="other" selectedClass="" class="btn btn-sm btn-dark" style="">other buffs</$button>')
	
	myprint(output, '\n---\n')

	dps_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		dps_sorted_stacking_uptime_Table.append([uptime_prof_name, DPSStats[uptime_prof_name]['Damage_Total'] / DPSStats[uptime_prof_name]['duration']])
	dps_sorted_stacking_uptime_Table = sorted(dps_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	dps_sorted_stacking_uptime_Table = list(map(lambda x: x[0], dps_sorted_stacking_uptime_Table))

	# Might
	myprint(output, '<$reveal type="match" state="$:/state/curDamageWithBuffs" text="might">\n')
	myprint(output, '\n---\n')

	# Might with damage table
	myprint(output, "|table-caption-top|k")
	myprint(output, "|{{Might}} Sortable table - Click header item to sort table {{Might}}|c")
	myprint(output, '|thead-dark table-hover sortable|k')
	output_header =  '|!Name | !Class | !DPS' 
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Avg| !1+ %| !5+ %| !10+ %| !15+ %| !20+ %| !25 %'
	output_header += '|h'
	myprint(output, output_header)
	
	for uptime_prof_name in dps_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_might'] / 1000) or 1
		damage_with_might = stacking_uptime_Table[uptime_prof_name]['damage_with_might']
		might_stacks = stacking_uptime_Table[uptime_prof_name]['might']

		if stacking_uptime_Table[uptime_prof_name]['duration_might'] * 10 < max_stacking_buff_fight_time:
			continue

		total_damage = DPSStats[uptime_prof_name]["Damage_Total"] or 1
		playerDPS = total_damage/DPSStats[uptime_prof_name]['duration']

		damage_with_avg_might = sum(stack_num * damage_with_might[stack_num] for stack_num in range(1, 26)) / total_damage
		damage_with_might_uptime = 1.0 - (damage_with_might[0] / total_damage)
		damage_with_might_5_uptime = sum(damage_with_might[i] for i in range(5,26)) / total_damage
		damage_with_might_10_uptime = sum(damage_with_might[i] for i in range(10,26)) / total_damage
		damage_with_might_15_uptime = sum(damage_with_might[i] for i in range(15,26)) / total_damage
		damage_with_might_20_uptime = sum(damage_with_might[i] for i in range(20,26)) / total_damage
		damage_with_might_25_uptime = damage_with_might[25] / total_damage
		
		avg_might = sum(stack_num * might_stacks[stack_num] for stack_num in range(1, 26)) / (fight_time * 1000)
		might_uptime = 1.0 - (might_stacks[0] / (fight_time * 1000))
		might_5_uptime = sum(might_stacks[i] for i in range(5,26)) / (fight_time * 1000)
		might_10_uptime = sum(might_stacks[i] for i in range(10,26)) / (fight_time * 1000)
		might_15_uptime = sum(might_stacks[i] for i in range(15,26)) / (fight_time * 1000)
		might_20_uptime = sum(might_stacks[i] for i in range(20,26)) / (fight_time * 1000)
		might_25_uptime = might_stacks[25] / (fight_time * 1000)


		output_string = '|'+name+' |'+' {{'+prof+'}} | '+my_value(round(playerDPS))+'| '+my_value(round(fight_time))

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_avg_might, 4))+'% dmg - '+"{:.2f}".format(round(avg_might, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_avg_might), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_5_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_5_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_5_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_10_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_10_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_10_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_15_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_15_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_15_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_20_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_20_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_20_uptime * 100), 4))+'</span>'

		output_string += '| <span data-tooltip="'+"{:.2f}".format(round(damage_with_might_25_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(might_25_uptime * 100, 4))+'% uptime">'
		output_string += "{:.2f}".format(round((damage_with_might_25_uptime * 100), 4))+'</span>'
		
		output_string += '|'

		myprint(output, output_string)

	myprint(output, "</$reveal>\n")

	# Other buffs with damage
	myprint(output, '<$reveal type="match" state="$:/state/curDamageWithBuffs" text="other">\n')
	myprint(output, '\n---\n')
		
	# Other buffs with damage table
	other_buffs_with_damage = ['stability', 'protection', 'aegis', 'fury', 'resistance', 'resolution', 'quickness', 'swiftness', 'alacrity', 'vigor', 'regeneration']
	myprint(output, "|table-caption-top|k")
	myprint(output, "|Sortable table - Click header item to sort table |c")
	myprint(output, '|thead-dark table-hover sortable|k')
	output_header =  '|!Name | !Class | !DPS '
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	for damage_buff in other_buffs_with_damage:
		output_header += '| !{{'+damage_buff.capitalize()+'}}'
	output_header += '|h'
	myprint(output, output_header)
	
	for uptime_prof_name in dps_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		prof = stacking_uptime_Table[uptime_prof_name]['profession']
		uptime_table_prof_name = "{{"+prof+"}} "+name

		uptime_fight_time = uptime_Table[uptime_table_prof_name]['duration'] or 1
		dps_fight_time = DPSStats[uptime_prof_name]['duration'] or 1
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_might'] / 1000) or 1

		if stacking_uptime_Table[uptime_prof_name]['duration_might'] * 10 < max_stacking_buff_fight_time:
			continue

		total_damage = DPSStats[uptime_prof_name]["Damage_Total"] or 1
		playerDPS = total_damage/dps_fight_time
		output_string = '|'+name+' |'+' {{'+prof+'}} | '+my_value(round(playerDPS))+'| '+my_value(round(fight_time))+'|'

		for damage_buff in other_buffs_with_damage:
			damage_with_buff = stacking_uptime_Table[uptime_prof_name]['damage_with_'+damage_buff]
			damage_with_buff_uptime = damage_with_buff[1] / total_damage			

			if damage_buff in uptime_Table[uptime_table_prof_name]:
				buff_uptime = uptime_Table[uptime_table_prof_name][damage_buff] / uptime_fight_time
			else:
				buff_uptime = 0

			output_string += ' <span data-tooltip="'+"{:.2f}".format(round(damage_with_buff_uptime * 100, 4))+'% dmg - '+"{:.2f}".format(round(buff_uptime * 100, 4))+'% uptime">'
			output_string += "{:.2f}".format(round((damage_with_buff_uptime * 100), 4))+'</span>|'

		myprint(output, output_string)

	myprint(output, "</$reveal>\n")

	myprint(output, "</$reveal>\n")
	#end Stacking Buff Uptime Table insert


	#start On Tag Death insert
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Death_OnTag">')    
	myprint(output, '\n<<alert dark "On Tag Death Review" width:60%>>\n\n')
	myprint(output, '\nAvg Dist calculation stops on initial player death or Tag Death to avoiding respawn range')
	myprint(output, '\nOn Tag Death Review Current Formula: (On Tag <= 600 Range, Off Tag >600 and <=5000, Run Back Death > 5000)\n')
	myprint(output, '\n---\n')
	myprint(output, '\n---\n')

	myprint(output, "|table-caption-top|k")
	myprint(output, "|Sortable table - Click header item to sort table |c")
	myprint(output, "|thead-dark table-hover sortable|k")
	myprint(output, "|!Name | !Profession | !Attendance | !Avg Dist| !On-Tag<br>{{Deaths}} |  !Off-Tag<br>{{Deaths}} | !After-Tag<br>{{Deaths}} |  !Run-Back<br>{{Deaths}} |  !Total<br>{{Deaths}} | Off-Tag Deaths Ranges |h")
	for deathOnTag_prof_name in Death_OnTag:
		name = Death_OnTag[deathOnTag_prof_name]['name']
		prof = Death_OnTag[deathOnTag_prof_name]['profession']
		fightTime = uptime_Table.get(deathOnTag_prof_name, {}).get('duration', 1)
		if len(Death_OnTag[deathOnTag_prof_name]["distToTag"]):
			Avg_Dist = round(sum(Death_OnTag[deathOnTag_prof_name]["distToTag"])/len(Death_OnTag[deathOnTag_prof_name]["distToTag"]))
		else:
			Avg_Dist = "N/A"

		if Death_OnTag[deathOnTag_prof_name]['Off_Tag']:
			converted_list = [str(round(element)) for element in Death_OnTag[deathOnTag_prof_name]['Ranges']]
			Ranges_string = ",".join(converted_list)
		else:
			Ranges_string = " "

		output_string = "|"+name+" |"
		output_string += " {{"+prof+"}} | "+my_value(round(fightTime))+" | "+str(Avg_Dist)+"| "+str(Death_OnTag[deathOnTag_prof_name]['On_Tag'])+" | "+str(Death_OnTag[deathOnTag_prof_name]['Off_Tag'])+" | "+str(Death_OnTag[deathOnTag_prof_name]['After_Tag_Death'])+" | "+str(Death_OnTag[deathOnTag_prof_name]['Run_Back'])+" | "+str(Death_OnTag[deathOnTag_prof_name]['Total'])+" |"+Ranges_string+" |"
	


		myprint(output, output_string)

	write_Death_OnTag_xls(Death_OnTag, uptime_Table, players, args.xls_output_filename)
	myprint(output, "</$reveal>\n")
	#end On Tag Death insert

	#Downed Healing
	down_Heal_Order = {14419: 'Battle Standard', 9163: 'Signet of Mercy', 5763: 'Renewal of Water', 5762: 'Renewal of Fire', 5760: 'Renewal of Air', 5761: 'Renewal of Earth', 10611: 'Signet of Undeath', 12596: "Nature's Renewal"}
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Downed_Healing">')    
	myprint(output, '\n<<alert dark "Healing to downed players" width:60%>>\n\n')
	myprint(output, '\nRequires Heal Stat addon for ARCDPS to track\n')
	myprint(output, '\n---\n')
	myprint(output, '\n---\n')

	myprint(output, '\n<div class="flex-row">\n<div class="flex-col border">\n')
	myprint(output, "\n!!Healing done\nWork in Progress more skills to be added when logs available\n")
	myprint(output, "|table-caption-top|k")
	myprint(output, "|Sortable table - Click header item to sort table |c")
	myprint(output, "|thead-dark table-hover sortable|k")
	output_string = "|!Name | !Profession | !Attendance |"
	for item in down_Heal_Order:
		output_string += "!{{"+down_Heal_Order[item]+"}}|"
	output_string += "h"
	myprint(output, output_string)
	for squadDps_prof_name in downed_Healing:
		name = downed_Healing[squadDps_prof_name]['name']
		prof = downed_Healing[squadDps_prof_name]['prof']
		fightTime = uptime_Table[squadDps_prof_name]['duration']

		output_string = "|"+name+" |{{"+prof+"}}|"+my_value(round(fightTime))+"| "
		for skill in down_Heal_Order:
			if down_Heal_Order[skill] in downed_Healing[squadDps_prof_name]:
				output_string += str(downed_Healing[squadDps_prof_name][down_Heal_Order[skill]]['Heals'])+"|"
			else:
				output_string += " |"
		myprint(output, output_string)
	
	myprint(output, '\n</div>\n<div class="flex-col border">\n')
	myprint(output, "\n!!Number of Skill Hits\nWork in Progress more skills to be added when logs available\n")
	myprint(output, "|table-caption-top|k")
	myprint(output, "|Sortable table - Click header item to sort table |c")
	myprint(output, "|thead-dark table-hover sortable|k")
	output_string = "|!Name | !Profession | !Attendance |"
	for item in down_Heal_Order:
		output_string += "!{{"+down_Heal_Order[item]+"}}|"
	output_string += "h"
	myprint(output, output_string)
	for squadDps_prof_name in downed_Healing:
		name = downed_Healing[squadDps_prof_name]['name']
		prof = downed_Healing[squadDps_prof_name]['prof']
		fightTime = uptime_Table[squadDps_prof_name]['duration']

		output_string = "|"+name+" |{{"+prof+"}}|"+my_value(round(fightTime))+"| "
		for skill in down_Heal_Order:
			if down_Heal_Order[skill] in downed_Healing[squadDps_prof_name]:
				output_string += str(downed_Healing[squadDps_prof_name][down_Heal_Order[skill]]['Hits'])+" |"
			else:
				output_string += " |"
		myprint(output, output_string)



	myprint(output, '\n</div>\n</div>\n</$reveal>\n')
	#End Downed Healing

	#start Offensive Stat Table insert
	offensive_Order = ['Critical',  'Flanking',  'Glancing',  'Moving',  'Blinded',  'Interupt',  'Invulnerable',  'Evaded',  'Blocked']
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Offensive Stats">')    
	myprint(output, '\n<<alert dark "Offensive Stats across all fights attended." width:60%>>\n\n')
	
	myprint(output, '\n---\n')
	myprint(output, '\n---\n')

	myprint(output, "|table-caption-top|k")
	myprint(output, "|Sortable table - Click header item to sort table |c")
	myprint(output, "|thead-dark table-hover sortable|k")
	myprint(output, "|!Name | !Profession | !{{Critical}}% |  !{{Flanking}}% |  !{{Glancing}}% |  !{{Moving}}% |  !{{Blind}} |  !{{Interupt}} |  !{{Invulnerable}} |  !{{Evaded}} |  !{{Blocked}} |h")
	for squadDps_prof_name in squad_offensive:
		name = squad_offensive[squadDps_prof_name]['name']
		prof = squad_offensive[squadDps_prof_name]['prof']

		output_string = "|"+name+" | {{"+prof+"}} | "

		#Calculate Critical_Hits_Rate
		if squad_offensive[squadDps_prof_name]['stats']['criticalRate']:
			Critical_Rate = round((squad_offensive[squadDps_prof_name]['stats']['criticalRate']/squad_offensive[squadDps_prof_name]['stats']['critableDirectDamageCount'])*100, 4)
		else:
			Critical_Rate = 0.0000
		Critical_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['criticalRate'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['critableDirectDamageCount'])+' critable hits">'+str(Critical_Rate)+'</span>'
		
		output_string += str(Critical_Rate_TT)+" | "
		
		#Calculate Flanking_Rate
		if squad_offensive[squadDps_prof_name]['stats']['flankingRate']:
			Flanking_Rate = round((squad_offensive[squadDps_prof_name]['stats']['flankingRate']/squad_offensive[squadDps_prof_name]['stats']['connectedDirectDamageCount'])*100, 4)
		else:
			Flanking_Rate = 0.0000
		Flanking_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['flankingRate'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['connectedDirectDamageCount'])+' connected direct hit(s)">'+str(Flanking_Rate)+'</span>'
		
		output_string += str(Flanking_Rate_TT)+" | "
		
		#Calculate Glancing Rate
		if squad_offensive[squadDps_prof_name]['stats']['glanceRate']:
			Glancing_Rate = round((squad_offensive[squadDps_prof_name]['stats']['glanceRate']/squad_offensive[squadDps_prof_name]['stats']['connectedDirectDamageCount'])*100, 4)
		else:
			Glancing_Rate = 0.0000
		Glancing_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['glanceRate'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['connectedDirectDamageCount'])+' connected direct hit(s)">'+str(Glancing_Rate)+'</span>'
		
		output_string += str(Glancing_Rate_TT)+" | "
		
		#Calculate Moving_Rate
		if squad_offensive[squadDps_prof_name]['stats']['againstMovingRate']:
			Moving_Rate = round((squad_offensive[squadDps_prof_name]['stats']['againstMovingRate']/squad_offensive[squadDps_prof_name]['stats']['totalDamageCount'])*100, 4)
		else:
			Moving_Rate = 0.0000
		Moving_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['againstMovingRate'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['totalDamageCount'])+' direct hit(s)">'+str(Moving_Rate)+'</span>'
		
		output_string += str(Moving_Rate_TT)+" | "
		
		#Calculate Blinded_Rate
		if squad_offensive[squadDps_prof_name]['stats']['missed']:
			Blinded_Rate = squad_offensive[squadDps_prof_name]['stats']['missed']
		else:
			Blinded_Rate = 0
		Blinded_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['missed'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['totalDamageCount'])+' direct hit(s)">'+str(Blinded_Rate)+'</span>'
		
		output_string += str(Blinded_Rate_TT)+" | "
		
		#Calculate Interupt_Rate
		if squad_offensive[squadDps_prof_name]['stats']['interrupts']:
			Interupt_Rate = squad_offensive[squadDps_prof_name]['stats']['interrupts']
		else:
			Interupt_Rate = 0		
		Interupt_Rate_TT = '<span data-tooltip="Interupted enemy players '+str(Interupt_Rate)+' time(s)">'+str(Interupt_Rate)+'</span>'
		
		output_string += str(Interupt_Rate_TT)+" | "
		
		#Calculate Invulnerable_Rate
		if squad_offensive[squadDps_prof_name]['stats']['invulned']:
			Invulnerable_Rate = squad_offensive[squadDps_prof_name]['stats']['invulned']
		else:
			Invulnerable_Rate = 0
		Invulnerable_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['invulned'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['totalDamageCount'])+' hit(s)">'+str(Invulnerable_Rate)+'</span>'
		
		output_string += str(Invulnerable_Rate_TT)+" | "
		
		#Calculate Evaded_Rate
		if squad_offensive[squadDps_prof_name]['stats']['evaded']:
			Evaded_Rate = squad_offensive[squadDps_prof_name]['stats']['evaded']
		else:
			Evaded_Rate = 0
		Evaded_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['evaded'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['connectedDirectDamageCount'])+' direct hit(s)">'+str(Evaded_Rate)+'</span>'
		
		output_string += str(Evaded_Rate_TT)+" | "
		
		#Calculate Blocked_Rate
		if squad_offensive[squadDps_prof_name]['stats']['blocked']:
			Blocked_Rate = squad_offensive[squadDps_prof_name]['stats']['blocked']
		else:
			Blocked_Rate = 0		
		Blocked_Rate_TT = '<span data-tooltip="'+str(squad_offensive[squadDps_prof_name]['stats']['blocked'])+' out of '+str(squad_offensive[squadDps_prof_name]['stats']['connectedDirectDamageCount'])+' direct hit(s)">'+str(Blocked_Rate)+'</span>'
		
		output_string += str(Blocked_Rate_TT)+" |"
		
		myprint(output, output_string)

	write_squad_offensive_xls(squad_offensive, args.xls_output_filename)
	myprint(output, "</$reveal>\n")
	#end Offensive Stat Table insert

	# Firebrand pages
	tome1_skill_ids = ["41258", "40635", "42449", "40015", "42898"]
	tome2_skill_ids = ["45022", "40679", "45128", "42008", "42925"]
	tome3_skill_ids = ["42986", "41968", "41836", "40988", "44455"]
	tome_skill_ids = [
		*tome1_skill_ids,
		*tome2_skill_ids,
		*tome3_skill_ids,
	]

	tome_skill_page_cost = {
		"41258": 1, "40635": 1, "42449": 1, "40015": 1, "42898": 1,
		"45022": 1, "40679": 1, "45128": 1, "42008": 2, "42925": 2,
		"42986": 1, "41968": 1, "41836": 2, "40988": 2, "44455": 2,
	}
	
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="FBPages">\n')    
	myprint(output, '\n<<alert dark "Firebrand Pages" width:60%>>\n\n')

	myprint(output, "|table-caption-top|k")
	myprint(output, "|Firebrand page utilization, pages/minute|c")
	myprint(output, '|thead-dark table-hover sortable|k')
	output_header =  '|!Name '
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !Pages/min| | !T1 {{Tome_of_Justice}}| !C1 {{Chapter_1_Searing_Spell}}| !C2 {{Chapter_2_Igniting_Burst}}| !C3 {{Chapter_3_Heated_Rebuke}}| !C4 {{Chapter_4_Scorched_Aftermath}}| !Epi {{Epilogue_Ashes_of_the_Just}}| | !T2 {{Tome_of_Resolve}} | !C1 {{Chapter_1_Desert_Bloom}}| !C2 {{Chapter_2_Radiant_Recovery}}| !C3 {{Chapter_3_Azure_Sun}}| !C4 {{Chapter_4_Shining_River}}| !Epi {{Epilogue_Eternal_Oasis}}|  | !T3 {{Tome_of_Courage}}| !C1 {{Chapter_1_Unflinching_Charge}}| !C2 {{Chapter_2_Daring_Challenge}}| !C3 {{Chapter_3_Valiant_Bulwark}}| !C4 {{Chapter_4_Stalwart_Stand}}| !Epi {{Epilogue_Unbroken_Lines}}'
	output_header += '|h'
	myprint(output, output_header)
	
	pages_sorted_stacking_uptime_Table = []
	for uptime_prof_name in stacking_uptime_Table:
		fight_time = (stacking_uptime_Table[uptime_prof_name]['duration_stability'] / 1000) or 1
		stability_stacks = stacking_uptime_Table[uptime_prof_name]['stability']

		if (DPSStats[uptime_prof_name]['duration'] * 100) / max_fightTime < config.min_attendance_percentage_for_top:
			continue

		firebrand_pages = stacking_uptime_Table[uptime_prof_name]['firebrand_pages']
		
		all_tomes_total = 0
		for skill_id in tome_skill_ids:
			all_tomes_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]

		pages_sorted_stacking_uptime_Table.append([uptime_prof_name, all_tomes_total / fight_time])
	pages_sorted_stacking_uptime_Table = sorted(pages_sorted_stacking_uptime_Table, key=lambda x: x[1], reverse=True)
	pages_sorted_stacking_uptime_Table = list(map(lambda x: x[0], pages_sorted_stacking_uptime_Table))

	def fmt_firebrand_page_total(page_casts, page_cost, fight_time, page_total):
		output_string = ' <span data-tooltip="'

		if page_cost:
			output_string += "{:.2f}".format(round(100 * page_casts * page_cost / page_total, 4))
			output_string += '% of total pages '
			output_string += "{:.2f}".format(round(60 * page_casts / fight_time, 4))
			output_string += ' casts / minute">'
		else:
			output_string += "{:.2f}".format(round(100 * page_casts / page_total, 4))
			output_string += '% of total pages">'

		if page_cost:
			output_string += "{:.2f}".format(round(60 * page_casts * page_cost / fight_time, 4))
		else:
			output_string += "{:.2f}".format(round(60 * page_casts / fight_time, 4))

		output_string += '</span>|'

		return output_string

	
	for uptime_prof_name in pages_sorted_stacking_uptime_Table:
		name = stacking_uptime_Table[uptime_prof_name]['name']
		role = stacking_uptime_Table[uptime_prof_name]['role']
		fight_time = DPSStats[uptime_prof_name]['duration'] or 1

		firebrand_pages = stacking_uptime_Table[uptime_prof_name]['firebrand_pages']
	
		tome1_total = 0
		for skill_id in tome1_skill_ids:
			tome1_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]
	
		tome2_total = 0
		for skill_id in tome2_skill_ids:
			tome2_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]
	
		tome3_total = 0
		for skill_id in tome3_skill_ids:
			tome3_total += firebrand_pages.get(skill_id, 0) * tome_skill_page_cost[skill_id]
	
		all_tomes_total = tome1_total + tome2_total + tome3_total

		if all_tomes_total == 0:
			continue

		output_string = '|'+name
		if role != "Support":
			output_string += ' (' + role + ')'
		output_string += ' | ' + my_value(round(fight_time))+' | '
		output_string += "{:.2f}".format(round(60 * all_tomes_total / fight_time, 4)) + '|'
		output_string += ' |'

		output_string += fmt_firebrand_page_total(tome1_total, 0, fight_time, all_tomes_total)
		for skill_id in tome1_skill_ids:
			page_total = firebrand_pages.get(skill_id, 0)
			page_cost = tome_skill_page_cost[skill_id]
			output_string += fmt_firebrand_page_total(page_total, page_cost, fight_time, all_tomes_total)
		output_string += " |"

		output_string += fmt_firebrand_page_total(tome2_total, 0, fight_time, all_tomes_total)
		for skill_id in tome2_skill_ids:
			page_total = firebrand_pages.get(skill_id, 0)
			page_cost = tome_skill_page_cost[skill_id]
			output_string += fmt_firebrand_page_total(page_total, page_cost, fight_time, all_tomes_total)
		output_string += " |"

		output_string += fmt_firebrand_page_total(tome3_total, 0, fight_time, all_tomes_total)
		for skill_id in tome3_skill_ids:
			page_total = firebrand_pages.get(skill_id, 0)
			page_cost = tome_skill_page_cost[skill_id]
			output_string += fmt_firebrand_page_total(page_total, page_cost, fight_time, all_tomes_total)

		myprint(output, output_string)

	myprint(output, "</$reveal>\n")
	#End Firebrand pages

	#start Dashboard insert
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Dashboard">')    
	myprint(output, '\n<<alert dark "Dashboard for various charts" width:60%>>\n\n')
	Dashboard_Charts = ["Kills/Downs/DPS", "Fury/Might/DPS", "Deaths/DamageTaken/DistanceFromTag", "Cleanses/Heals/BoonScore", "BoonStrips/OutgoingControlScore/DPS", "Profession_DPS_BoxPlot", "Player_DPS_BoxPlot", "Profession_SPS_BoxPlot", "Player_SPS_BoxPlot", "Profession_CPS_BoxPlot", "Player_CPS_BoxPlot", "Profession_HPS_BoxPlot", "Player_HPS_BoxPlot"]
	
	for chart in Dashboard_Charts:
		myprint(output, '<$button setTitle="$:/state/curChart" setTo="'+chart+'" selectedClass="" class="btn btn-sm btn-dark" style="">'+chart+' </$button>')
	
	myprint(output, '\n---\n')
	

	for chart in Dashboard_Charts:
			myprint(output, '<$reveal type="match" state="$:/state/curChart" text="'+chart+'">\n')
			myprint(output, '\n---\n')
			myprint(output, '\n<div class="flex-row">\n    <div class="flex-col border">\n')

			if chart == "Kills/Downs/DPS":
				myprint(output, "\n!!Kills / Downs / DPS\n")
				myprint(output, ",,Bubble Size based on DPS output,,\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_kills_BubbleChartData}} $height="500px" $theme="dark"/>')

			if chart == "Fury/Might/DPS":
				myprint(output, "\n!!Kills / Downs / DPS\n")
				myprint(output, ",,Bubble Size based on DPS output,,\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_fury_might_BubbleChartData}} $height="500px" $theme="dark"/>')

			if chart == "Deaths/DamageTaken/DistanceFromTag":
				myprint(output, "\n!!Deaths / Damage Taken / Distance from Tag\n")
				myprint(output, ",,Bubble Size based on Average Distance to Tag,,\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_deaths_BubbleChartData}} $height="500px" $theme="dark"/>')

			if chart == "Cleanses/Heals/BoonScore":
				myprint(output, "\n!!Cleanses / Heals / Boon Score\n")
				myprint(output, ",,Bubble Size based on Boon Score = Sum of all average Boon and Aura output,,\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_cleanse_BubbleChartData}} $height="500px" $theme="dark"/>')

			if chart == "BoonStrips/OutgoingControlScore/DPS":
				myprint(output, "\n!!Boon Strips / Outgoing Control Score / DPS\n")
				myprint(output, ",,Bubble Size based on Control Score = Sum of all outgoing control effects,,\n")
				myprint(output, ",,Bubble Size based on DPS output,,\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_rips_BubbleChartData}} $height="500px" $theme="dark"/>')

			#Profession_DPS_BoxPlot
			if chart == "Profession_DPS_BoxPlot":
				myprint(output, "\n!!Damage per Second Box Plot by Profession\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_DPS_Profession_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Player_DPS_BoxPlot
			if chart == "Player_DPS_BoxPlot":
				myprint(output, "\n!!Damage per Second Box Plot by Player\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_DPS_Profession_and_Name_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Profession_SPS_BoxPlot
			if chart == "Profession_SPS_BoxPlot":
				myprint(output, "\n!!Boon Strip per Second Box Plot by Profession\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_SPS_Profession_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Player_SPS_BoxPlot
			if chart == "Player_SPS_BoxPlot":
				myprint(output, "\n!!Boon Strip per Second Box Plot by Player\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_SPS_Profession_and_Name_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Profession_CPS_BoxPlot
			if chart == "Profession_CPS_BoxPlot":
				myprint(output, "\n!!Cleanses per Second Box Plot by Profession\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_CPS_Profession_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Player_CPS_BoxPlot
			if chart == "Player_CPS_BoxPlot":
				myprint(output, "\n!!Cleanses per Second Box Plot by Player\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_CPS_Profession_and_Name_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Profession_HPS_BoxPlot
			if chart == "Profession_HPS_BoxPlot":
				myprint(output, "\n!!Heals per Second Box Plot by Profession\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_HPS_Profession_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			#Player_HPS_BoxPlot
			if chart == "Player_HPS_BoxPlot":
				myprint(output, "\n!!Heals per Second Box Plot by Player\n")
				myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_HPS_Profession_and_Name_Box_PlotChartData}} $height="800px" $theme="dark"/>')

			myprint(output, '\n</div>\n</div>\n')
			myprint(output, "</$reveal>\n")

	myprint(output, "</$reveal>\n")
	#end Dashboard insert

	#start DPS Stats insert		
	sorted_DPSStats = []
	for DPSStats_prof_name in DPSStats:
		name = DPSStats[DPSStats_prof_name]['name']
		prof = DPSStats[DPSStats_prof_name]['profession']
		fightTime = DPSStats[DPSStats_prof_name]['duration'] or 1

		if DPSStats[DPSStats_prof_name]['Damage_Total'] / fightTime < 250 or (fightTime * 100) / max_fightTime < config.min_attendance_percentage_for_top:
			continue

		sorted_DPSStats.append([DPSStats_prof_name, DPSStats[DPSStats_prof_name]['Damage_Total'] / fightTime])
	sorted_DPSStats = sorted(sorted_DPSStats, key=lambda x: x[1], reverse=True)
	sorted_DPSStats = list(map(lambda x: x[0], sorted_DPSStats))

	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="DPSStats">')    
	myprint(output, '\n<<alert dark "Experimental DPS stats" width:60%>>\n\n')
	
	myprint(output, '\n---\n')
	myprint(output, '!!! `Chunk Damage(t)` [`Ch(t)DPS`] \n')
	myprint(output, '!!! Damage done `t` seconds before an enemy goes down \n')
	myprint(output, '!!! `Carrior Damage` [`CaDPS`] \n')
	myprint(output, '!!! Damage done to down enemies that die \n')
	myprint(output, '\n---\n')

	myprint(output, '|table-caption-top|k')
	myprint(output, '|Sortable table - Click header item to sort table |c')
	myprint(output, '|thead-dark table-hover sortable|k')
	output_header =  '|!Name | !Class'
	output_header += ' | ! <span data-tooltip="Number of seconds player was in squad logs">Seconds</span>'
	output_header += '| !DPS| !Ch2DPS| !Ch4DPS| !Ch8DPS| !CaDPS'
	output_header += '|h'
	myprint(output, output_header)
	for DPSStats_prof_name in sorted_DPSStats:
		name = DPSStats[DPSStats_prof_name]['name']
		prof = DPSStats[DPSStats_prof_name]['profession']
		fightTime = DPSStats[DPSStats_prof_name]['duration'] or 1

		output_string = '|'+name+' |'+' {{'+prof+'}} | '+my_value(fightTime)
		output_string += '| '+'<span data-tooltip="'+my_value(DPSStats[DPSStats_prof_name]['Damage_Total'])+' total damage">'+my_value(round(DPSStats[DPSStats_prof_name]['Damage_Total'] / fightTime))+'</span>'
		output_string += '| '+'<span data-tooltip="'+my_value(DPSStats[DPSStats_prof_name]['Chunk_Damage'][2])+' chunk(2) damage">'+my_value(round(DPSStats[DPSStats_prof_name]['Chunk_Damage'][2] / fightTime))+'</span>'
		output_string += '| '+'<span data-tooltip="'+my_value(DPSStats[DPSStats_prof_name]['Chunk_Damage'][4])+' chunk (4) damage">'+my_value(round(DPSStats[DPSStats_prof_name]['Chunk_Damage'][4] / fightTime))+'</span>'
		output_string += '| '+'<span data-tooltip="'+my_value(DPSStats[DPSStats_prof_name]['Chunk_Damage'][8])+' chunk (8) damage">'+my_value(round(DPSStats[DPSStats_prof_name]['Chunk_Damage'][8] / fightTime))+'</span>'
		output_string += '| '+'<span data-tooltip="'+my_value(DPSStats[DPSStats_prof_name]['Carrion_Damage'])+' carrion damage">'+my_value(round(DPSStats[DPSStats_prof_name]['Carrion_Damage'] / fightTime))+'</span>'
		output_string += '|'

		myprint(output, output_string)

	write_DPSStats_xls(DPSStats, args.xls_output_filename)
	myprint(output, '\n---\n')
	myprint(output, "\n!!DPS Stats Bubble Chart\n")
	myprint(output, "\n,,Bubble size based on CDPS,,\n")
	myprint(output, '<$echarts $text={{'+fileDate.strftime("%Y%m%d%H%M")+'_DPSStats_BubbleChartData}} $height="500px" $theme="dark"/>')
	myprint(output, "</$reveal>\n")
	#end DPS Stats insert

	# Burst Damage
	myprint(output, '<$reveal type="match" state="$:/state/curTab" text="Burst Damage">\n')    
	myprint(output, '\n<<alert dark "Experimental DPS stats" width:60%>>\n\n')
	
	myprint(output, '---\n')
	myprint(output, '!!! `Burst Damage(t)` [`Bur(t)`] \n')
	myprint(output, '!!! Maximum damage done over any `t` second interval \n')
	myprint(output, '---\n')
	myprint(output, '!!! `Ch5Ca Burst Damage(t)` [`Ch5CaBur(t)`] \n')
	myprint(output, '!!! Maximum Chunk(5) + Carrion damage done over any `t` second interval \n')
	myprint(output, '---\n')

	burst_menu_string = '| '
	burst_menu_string += '<$radio tiddler="$:/temp/BurstDamage" field="curBurstTableDamage" value="Ch5Ca">Ch5Ca Damage</$radio>&nbsp; &nbsp;<$radio tiddler="$:/temp/BurstDamage" field="curBurstTableDamage" value="Damage"> Total Damage</$radio>'
	burst_menu_string += '&nbsp;&nbsp;/&nbsp;&nbsp;'
	burst_menu_string += '<$radio tiddler="$:/temp/BurstDamage" field="curBurstTableType" value="Cumulative">&nbsp;Cumulative</$radio>&nbsp; &nbsp;<$radio tiddler="$:/temp/BurstDamage" field="curBurstTableType" value="PS">&nbsp;PS</$radio>'
	burst_menu_string += ' |c'

	# First the per second version of the table
	myprint(output, '<$reveal type="match" stateTitle= "$:/temp/BurstDamage" stateField="curBurstTableDamage" text="Damage">\n')
	myprint(output, '<$reveal type="match" stateTitle= "$:/temp/BurstDamage" stateField="curBurstTableType" text="PS">\n')

	myprint(output, '|table-caption-top|k')
	myprint(output, burst_menu_string)
	myprint(output, '|thead-dark table-hover sortable|k')
	
	output_string = '|!Name | !Class |'

	for i in list(range(1, 6)) + list(range(10, 21, 5)):
		output_string += " !"+str(i)+"s |"
		
	output_string += "h"
	myprint(output, output_string)

	for DPSStats_prof_name in sorted_DPSStats:
		name = DPSStats[DPSStats_prof_name]['name']
		prof = DPSStats[DPSStats_prof_name]['profession']
		fightTime = DPSStats[DPSStats_prof_name]['duration']

		output_string = '|'+name+' |'+' {{'+prof+'}} | '
		for i in list(range(1, 6)) + list(range(10, 21, 5)):
			output_string += ' '+my_value(round(DPSStats[DPSStats_prof_name]['Burst_Damage'][i] / i))+'|'
				
		myprint(output, output_string)

	myprint(output, "\n</$reveal>\n")

	# Next the cumulative version of the table
	myprint(output, '<$reveal type="match" stateTitle= "$:/temp/BurstDamage" stateField="curBurstTableType" text="Cumulative">\n')

	myprint(output, '|table-caption-top|k')
	myprint(output, burst_menu_string)
	myprint(output, '|thead-dark table-hover sortable|k')
	
	output_string = '|!Name | !Class |'

	for i in list(range(1, 6)) + list(range(10, 21, 5)):
		output_string += " !"+str(i)+"s |"
		
	output_string += "h"
	myprint(output, output_string)

	for DPSStats_prof_name in sorted_DPSStats:
		name = DPSStats[DPSStats_prof_name]['name']
		prof = DPSStats[DPSStats_prof_name]['profession']
		fightTime = DPSStats[DPSStats_prof_name]['duration'] or 1

		output_string = '|'+name+' |'+' {{'+prof+'}} | '
		for i in list(range(1, 6)) + list(range(10, 21, 5)):
			output_string += ' '+my_value(DPSStats[DPSStats_prof_name]['Burst_Damage'][i])+'|'
				
		myprint(output, output_string)

	myprint(output, "\n</$reveal>\n")
	myprint(output, "\n</$reveal>\n")

	# Ch5Ca Burst Damage
	# First the per second version of the table
	myprint(output, '<$reveal type="match" stateTitle= "$:/temp/BurstDamage" stateField="curBurstTableDamage" text="Ch5Ca">\n')
	myprint(output, '<$reveal type="match" stateTitle= "$:/temp/BurstDamage" stateField="curBurstTableType" text="PS">\n')

	myprint(output, '|table-caption-top|k')
	myprint(output, burst_menu_string)
	myprint(output, '|thead-dark table-hover sortable|k')
	
	output_string = '|!Name | !Class |'

	for i in list(range(1, 6)) + list(range(10, 21, 5)):
		output_string += " !"+str(i)+"s |"
		
	output_string += "h"
	myprint(output, output_string)

	for DPSStats_prof_name in sorted_DPSStats:
		name = DPSStats[DPSStats_prof_name]['name']
		prof = DPSStats[DPSStats_prof_name]['profession']
		fightTime = DPSStats[DPSStats_prof_name]['duration'] or 1

		output_string = '|'+name+' |'+' {{'+prof+'}} | '
		for i in list(range(1, 6)) + list(range(10, 21, 5)):
			output_string += ' '+my_value(round(DPSStats[DPSStats_prof_name]['Ch5Ca_Burst_Damage'][i] / i))+'|'
				
		myprint(output, output_string)

	myprint(output, "\n</$reveal>\n")

	# Next the cumulative version of the table
	myprint(output, '<$reveal type="match" stateTitle= "$:/temp/BurstDamage" stateField="curBurstTableType" text="Cumulative">\n')

	myprint(output, '|table-caption-top|k')
	myprint(output, burst_menu_string)
	myprint(output, '|thead-dark table-hover sortable|k')
	
	output_string = '|!Name | !Class |'

	for i in list(range(1, 6)) + list(range(10, 21, 5)):
		output_string += " !"+str(i)+"s |"
		
	output_string += "h"
	myprint(output, output_string)

	for DPSStats_prof_name in sorted_DPSStats:
		name = DPSStats[DPSStats_prof_name]['name']
		prof = DPSStats[DPSStats_prof_name]['profession']
		fightTime = DPSStats[DPSStats_prof_name]['duration'] or 1

		output_string = '|'+name+' |'+' {{'+prof+'}} | '
		for i in list(range(1, 6)) + list(range(10, 21, 5)):
			output_string += ' '+my_value(DPSStats[DPSStats_prof_name]['Ch5Ca_Burst_Damage'][i])+'|'
				
		myprint(output, output_string)

	myprint(output, "\n</$reveal>\n")
	myprint(output, "\n</$reveal>\n")

	myprint(output, "\n</$reveal>\n")     
	# end Ch5Ca Burst Damage

	top_players_by_stat = top_average_stat_players if config.player_sorting_stat_type == 'average' else top_total_stat_players
	for stat in config.stats_to_compute:
		skip_boxplot_charts = ['deaths', 'iol', 'stealth', 'HiS']
		#boxplot_Stats = ['stability',  'protection', 'aegis', 'might', 'fury', 'resistance', 'resolution', 'quickness', 'swiftness', 'alacrity', 'vigor', 'regeneration', 'res', 'kills', 'downs', 'swaps', 'dmg', 'Pdmg', 'Cdmg', 'rips', 'cleanses', 'superspeed', 'barrierDamage']
		if stat == 'dist':
			write_stats_xls(players, top_percentage_stat_players[stat], stat, args.xls_output_filename)
			if config.charts:
				#write_stats_chart(players, top_percentage_stat_players[stat], stat, myDate, args.input_directory, config)
				write_stats_box_plots(players, top_percentage_stat_players[stat], stat, ProfessionColor, myDate, args.input_directory, config)
		#elif stat == 'dmg_taken':
		#	write_stats_xls(players, top_average_stat_players[stat], stat, args.xls_output_filename)
		#	if config.charts:
		#		#write_stats_chart(players, top_average_stat_players[stat], stat, myDate, args.input_directory, config)
		#		write_stats_box_plots(players, top_average_stat_players[stat], stat, ProfessionColor, myDate, args.input_directory, config)
		elif stat == 'heal' and found_healing:
			write_stats_xls(players, top_players_by_stat[stat], stat, args.xls_output_filename)
			if config.charts:
				#write_stats_chart(players, top_players_by_stat[stat], stat, myDate, args.input_directory, config)
				write_stats_box_plots(players, top_players_by_stat[stat], stat, ProfessionColor, myDate, args.input_directory, config)
		elif stat == 'barrier' and found_barrier:
			write_stats_xls(players, top_players_by_stat[stat], stat, args.xls_output_filename)
			if config.charts:
				#write_stats_chart(players, top_players_by_stat[stat], stat, myDate, args.input_directory, config)
				write_stats_box_plots(players, top_players_by_stat[stat], stat, ProfessionColor, myDate, args.input_directory, config)
		#elif stat == 'deaths':
		#	write_stats_xls(players, top_consistent_stat_players[stat], stat, args.xls_output_filename)
		#	if config.charts:
		#		write_stats_chart(players, top_consistent_stat_players[stat], stat, myDate, args.input_directory, config)
		elif stat not in skip_boxplot_charts:
			write_stats_xls(players, top_players_by_stat[stat], stat, args.xls_output_filename)
			if config.charts:
				#write_stats_chart(players, top_players_by_stat[stat], stat, myDate, args.input_directory, config)
				write_stats_box_plots(players, top_players_by_stat[stat], stat, ProfessionColor, myDate, args.input_directory, config)
		else:
			write_stats_xls(players, top_players_by_stat[stat], stat, args.xls_output_filename)
			if config.charts:
				write_stats_chart(players, top_players_by_stat[stat], stat, myDate, args.input_directory, config)
				#write_stats_box_plots(players, top_players_by_stat[stat], stat, ProfessionColor, myDate, args.input_directory, config)
		if stat == 'rips' or stat == 'cleanses' or stat == 'stability' or stat == 'heal':
			supportCount = write_support_xls(players, top_players_by_stat[stat], stat, args.xls_output_filename, supportCount)

	#write out Bubble Charts and Box_Plots
	write_bubble_charts(players, top_players_by_stat[stat], squad_Control, myDate, args.input_directory)
	if include_comp_and_review:
		write_spike_damage_heatmap(squad_damage_output, myDate, args.input_directory)
	write_box_plot_charts(DPS_List, myDate, args.input_directory, "DPS")
	write_box_plot_charts(SPS_List, myDate, args.input_directory, "SPS")
	write_box_plot_charts(CPS_List, myDate, args.input_directory, "CPS")
	write_box_plot_charts(HPS_List, myDate, args.input_directory, "HPS")
	write_DPSStats_bubble_charts(uptime_Table, DPSStats, myDate, args.input_directory)
	write_Attendance_xls(Attendance, args.xls_output_filename)