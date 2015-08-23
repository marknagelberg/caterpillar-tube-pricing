
import pandas as pd
import evaluation
from sklearn.ensemble import RandomForestRegressor
import csv
from sklearn.preprocessing import Imputer
from sklearn import ensemble, preprocessing
import numpy as np
from sklearn.preprocessing import LabelEncoder
import os
import csv
import xgboost as xgb
import pickle

def get_adjacent_tube_assembly_ids(tube_assembly_id):
	tube_assembly_num = int(tube_assembly_id[3:])
	tube_assembly_down = str(tube_assembly_num - 1)
	tube_assembly_up = str(tube_assembly_num + 1)
	while len(tube_assembly_down) < 5:
		tube_assembly_down = '0' + tube_assembly_down
	while len(tube_assembly_up) < 5:
		tube_assembly_up = '0' + tube_assembly_up

	return ('TA-' + tube_assembly_down, 'TA-' + tube_assembly_up)

def extract(data):
	
	#tube_data = pd.read_csv('competition_data/tube.csv').fillna("")
	tube_data = pd.read_csv('competition_data/tube.csv').fillna("")
	data_merged = pd.merge(left = data, right = tube_data, how='inner', on='tube_assembly_id')
	bill_of_materials = pd.read_csv('competition_data/bill_of_materials.csv')
	data_merged = pd.merge(left = data_merged, right = bill_of_materials, how='inner', on='tube_assembly_id')

	data_merged['bracket_pricing'] = LabelEncoder().fit_transform(data_merged['bracket_pricing'])

	data_merged['quote_year'] = [int(x.split('-')[0]) for x in data_merged['quote_date']]
	data_merged['quote_month'] = [int(x.split('-')[1]) for x in data_merged['quote_date']]

	data_merged['end_a_1x'] = LabelEncoder().fit_transform(data_merged['end_a_1x'])
	data_merged['end_a_2x'] = LabelEncoder().fit_transform(data_merged['end_a_2x'])
	data_merged['end_x_1x'] = LabelEncoder().fit_transform(data_merged['end_x_1x'])
	data_merged['end_x_2x'] = LabelEncoder().fit_transform(data_merged['end_x_2x'])

	end_form = pd.read_csv('competition_data/tube_end_form.csv')

	data_merged.loc[data_merged['end_a'] == "NONE", 'end_a_forming'] = -1
	data_merged.loc[data_merged['end_x'] == "NONE", 'end_x_forming'] = -1

	for idx,row in end_form.iterrows():
		if row['forming'] == 'Yes':
			end_forming_value = 1
		if row['forming'] == 'No':
			end_forming_value = 0

		data_merged.loc[data_merged['end_a'] == row['end_form_id'], 'end_a_forming'] = end_forming_value
		data_merged.loc[data_merged['end_x'] == row['end_form_id'], 'end_x_forming'] = end_forming_value

	quantity_vars = [x for x in data_merged.columns.values if x[:9] == 'quantity_']
	data_merged[quantity_vars] = data_merged[quantity_vars].fillna(0, axis = 1)
	data_merged['total_quantity_components'] = data_merged[quantity_vars].sum(axis = 1)
	data_merged = data_merged.fillna("")

	'''
	type_component = pd.read_csv('competition_data/type_component.csv')
	for component_type_id in type_component['component_type_id']:
		data_merged[component_type_id] = 0
	data_merged['OTHER'] = 0

	with open('competition_data/components.csv', 'rb') as csvfilereader:
		with open('competition_data/components_v2.csv', 'wb') as csvfilewriter:
			reader = csv.reader(csvfilereader)
			writer = csv.writer(csvfilewriter)
			for row in reader:
				if len(row) == 4:
					del row[2]
					writer.writerow(row)
				else:
					writer.writerow(row)


	component = pd.read_csv('competition_data/components_v2.csv')
	component_mapping = {}
	for idx, row in component.iterrows():
		component_mapping[row['component_id']] = row['component_type_id']
	component_vars = ['component_id_' + str(x) for x in range(1,9)]
	for idx, row in data_merged.iterrows():
		for var in component_vars:
			if row[var] in component_mapping:
				data_merged.set_value(idx, component_mapping[row[var]], 1)
	'''

	#Additional processing of component data and adding it to train/test.
	comp_files = ['comp_adaptor.csv', 'comp_boss.csv', 'comp_elbow.csv', 'comp_float.csv', 'comp_hfl.csv', 'comp_nut.csv', 'comp_other.csv', 'comp_sleeve.csv', 'comp_straight.csv', 'comp_tee.csv', 'comp_threaded.csv']
	component_names = ['component_id_' + str(x) for x in range(1, 9)]
	concat_final_output = []

	#Build a dictionary with component_id as key, and value a dictionary of variables an values it can take.
	comp_variables = {}
	for comp_filename in comp_files:
		comp_file = pd.read_csv('competition_data/' + comp_filename)
		with open('competition_data/' + comp_filename) as csvfile:
			comp_reader = csv.DictReader(csvfile)
			for row in comp_reader:
				comp_variables[row['component_id']] = row

	counter = {x:0 for x in range(10)}
	
	#Add all of the relevant component data.
	for idx, row in data_merged.iterrows():
		count = 0

		weight = 0.0
		names = []
		orientation_yes = 0
		orientation_no = 0
		diameter = -1
		total_nominal_size = 0
		thread_pitch = 0
		adaptor_angle = 0
		total_length = 0
		head_diameter = 0
		corresponding_shell = []
		outside_shape = []
		outside_shape_round = 0
		outside_shape_hex = 0
		outside_shape_na = 0
		total_base_diameter = 0
		total_thread_size = 0
		thread_count = 0
		connection_type_counter = {'B-001':0, 'B-002':0,'B-003':0,'B-004':0,'B-005':0,'B-006':0,'B-007':0,'B-008':0,'B-009':0,'B-010':0,'B-011':0,'B-012':0,'B-013':0, '9999':0}
		connection_type_ids = ["connection_type_id_" + str(x) for x in range(1,5)]
		connection_type_ids.append("connection_type_id")
		nut_and_sleeve_length = 0
		thickness = 0
		mj_plug_class_code = 0
		base_type_flatbottom = 0
		base_type_shoulder = 0
		base_type_saddle = 0
		hex_size = 0
		seat_angle = 0
		thread_size = 0
		type_boss = 0
		type_stud = 0
		end_form_ids = {'A-00' + str(x):0 for x in range(1,8)}
		intended_nut_pitch = 0
		bolt_pattern_wide = 0
		plug_diameter = 0
		hex_nut_size = 0
		height_over_tube = 0
		shoulder_diameter = 0
		overall_length = 0
		extension_length = 0
		intended_nut_thread = 0
		mj_class_code_exists = 0
		unique_feature_yes = 0
		unique_feature_no = 0
		drop_length = 0
		elbow_angle = 0
		bolt_pattern_long = 0
		thread_pitches = {'thread_pitch_' + str(x):0 for x in range(1,5)}
		groove_no = 0
		groove_yes = 0

		num_components = 0
		#Get the component names you'll be working with for the row
		for name in component_names:
			if row[name] != '' and row[name] != '9999':
				names.append(row[name])
			if row[name] != '':
				num_components += 1
		if names:
			for name in names:
				if comp_variables[name]['weight'] != 'NA':
					weight += float(comp_variables[name]['weight'])
				if 'orientation' in comp_variables[name]:
					if comp_variables[name]['orientation'] == 'Yes':
						orientation_yes += 1
					if comp_variables[name]['orientation'] == 'No':
						orientation_no += 1
				if 'diameter' in comp_variables[name]:
					if comp_variables[name]['diameter'] != 'NA':
						diameter = float(comp_variables[name]['diameter'])
				if 'nominal_size_1' in comp_variables[name]:
					#Get nominal sizes (there are 4 in one file and 2 in another)
					nominal_sizes = [x for x in comp_variables[name] if x[0:13] == 'nominal_size_']
					total_nominal_size = sum(float(comp_variables[name][x]) for x in nominal_sizes if comp_variables[name][x] != 'NA' and comp_variables[name][x] != 'See Drawing')
				#Note - a lot of records have a thread pitch - is it possible something can have multiple 
				#components and thus multiple thread pitches? If so, want to think of proper way to aggregate.
				if 'thread_pitch' in comp_variables[name]:
					thread_pitch = comp_variables[name]['thread_pitch']
				if 'adaptor_angle' in comp_variables[name]:
					if comp_variables[name]['adaptor_angle'] != 'NA':
						adaptor_angle = comp_variables[name]['adaptor_angle']
				if 'length_1' in comp_variables[name]:
					#Get lengths (there are 4 in one file and 2 in another)
					lengths = [x for x in comp_variables[name] if x[0:7] == 'length_']
					total_length = sum(float(comp_variables[name][x]) for x in lengths if comp_variables[name][x] != 'NA')
				if 'head_diameter' in comp_variables[name]:
					if comp_variables[name]['head_diameter'] != 'NA':
						head_diameter = comp_variables[name]['head_diameter']
				#There are no tubes with multiple components with corresponding shell
				if 'corresponding_shell' in comp_variables[name]:
					corresponding_shell.append(comp_variables[name]['corresponding_shell'])
				#There are some tubes with multiple components with corresponding shell
				if 'outside_shape' in comp_variables[name]:
					if comp_variables[name]['outside_shape'] == "Round":
						outside_shape_round += 1
					if comp_variables[name]['outside_shape'] == "NA":
						outside_shape_na += 1
					if comp_variables[name]['outside_shape'] == "Hex":
						outside_shape_hex += 1
				if 'base_diameter' in comp_variables[name]:
					if comp_variables[name]['base_diameter'] != 'NA':
						total_base_diameter += float(comp_variables[name]['base_diameter'])
				if 'thread_size' in comp_variables[name]:
					thread_count += 1
					if comp_variables[name]['thread_size'][0] == 'M':
						#http://www.engineeringtoolbox.com/metric-threads-d_777.html
						total_thread_size += float(comp_variables[name]['thread_size'][1:]) * 0.03937
					else:
						total_thread_size += float(comp_variables[name]['thread_size'])
				if 'connection_type_id_1' in comp_variables[name] or 'connection_type_id' in comp_variables[name]:
					for connection_type in connection_type_ids:
						if connection_type in comp_variables[name] and comp_variables[name][connection_type] != 'NA':
							connection_type_counter[comp_variables[name][connection_type]] += 1
				if 'length' in comp_variables[name]:
					if comp_variables[name]['length'] != '9999':
						nut_and_sleeve_length += float(comp_variables[name]['length'])

				if 'thickness' in comp_variables[name]:
					if comp_variables[name]['thickness'] != 'NA':
						thickness += float(comp_variables[name]['thickness'])
				if 'mj_plug_class_code' in comp_variables[name] and comp_variables[name]['mj_plug_class_code'] != 'NA':
					mj_plug_class_code += 1
				if 'base_type' in comp_variables[name]:
					if comp_variables[name]['base_type'] == "Shoulder":
						base_type_shoulder += 1
					if comp_variables[name]['base_type'] == "Flat Bottom":
						base_type_flatbottom += 1
					if comp_variables[name]['base_type'] == "Saddle":
						base_type_saddle += 1
				if 'hex_size' in comp_variables[name] and comp_variables[name]['hex_size'] != 'NA':
					hex_size += float(comp_variables[name]['hex_size'])
				if 'seat_angle' in comp_variables[name] and comp_variables[name]['seat_angle'] != 'NA':
					seat_angle += float(comp_variables[name]['seat_angle'])
				if 'thread_size_1' in comp_variables[name]:
					thread_size_varnames = ['thread_size_1', 'thread_size_2', 'thread_size_3', 'thread_size_4']
					for size in thread_size_varnames:
						if size in comp_variables[name] and comp_variables[name][size] != 'NA':
							thread_size += float(comp_variables[name][size])
				if 'type' in comp_variables[name]:
					if comp_variables[name]['type'] == 'Boss':
						type_boss += 1
					elif comp_variables[name]['type'] == 'Stud':
						type_stud += 1
				if 'end_form_id_1' in comp_variables[name]:
					end_form_id_names = ['end_form_id_1', 'end_form_id_2', 'end_form_id_3', 'end_form_id_4']
					for id_name in end_form_id_names:
						if id_name in comp_variables[name] and comp_variables[name][id_name] != 'NA' and comp_variables[name][id_name] != "9999":
							end_form_ids[comp_variables[name][id_name]] += 1
				#Skipped "material" variable.
				if 'intended_nut_pitch' in comp_variables[name]:
					intended_nut_pitch += float(comp_variables[name]['intended_nut_pitch'])
				if 'bolt_pattern_wide' in comp_variables[name] and comp_variables[name]['bolt_pattern_wide'] != "NA":
					bolt_pattern_wide += float(comp_variables[name]['bolt_pattern_wide'])
				if 'plug_diameter' in comp_variables[name] and comp_variables[name]['plug_diameter'] != "NA":
					plug_diameter += float(comp_variables[name]['plug_diameter'])
				if 'hex_nut_size' in comp_variables[name] and comp_variables[name]['hex_nut_size'] != "NA":
					hex_nut_size += float(comp_variables[name]['hex_nut_size'])
				#Skipped "blind_hole" variable
				#Skipped "hose_diameter" variable
				if 'height_over_tube' in comp_variables[name] and comp_variables[name]['height_over_tube'] != "NA":
					height_over_tube += float(comp_variables[name]['height_over_tube'])
				if 'shoulder_diameter' in comp_variables[name] and comp_variables[name]['shoulder_diameter'] != "NA":
					shoulder_diameter += float(comp_variables[name]['shoulder_diameter'])
				if 'overall_length' in comp_variables[name] and comp_variables[name]['overall_length'] != "NA":
					overall_length += float(comp_variables[name]['overall_length'])
				#Skipped "part_name" variable
				if 'extension_length' in comp_variables[name] and comp_variables[name]['extension_length'] != "NA":
					extension_length += float(comp_variables[name]['extension_length'])
				if 'intended_nut_thread' in comp_variables[name] and comp_variables[name]['intended_nut_thread'] != "NA":
					intended_nut_thread += float(comp_variables[name]['intended_nut_thread'])
				if 'mj_class_code' in comp_variables[name] and comp_variables[name]['mj_class_code'] != "NA":
					mj_class_code_exists = 1

				if 'unique_feature' in comp_variables[name] and comp_variables[name]['unique_feature'] != "NA":
					if comp_variables[name]['unique_feature'] == "Yes":
						unique_feature_yes += 1
					if comp_variables[name]['unique_feature'] == "No":
						unique_feature_no += 1
				if 'drop_length' in comp_variables[name] and comp_variables[name]['drop_length'] != "NA":
					drop_length += float(comp_variables[name]['drop_length'])
				if 'elbow_angle' in comp_variables[name] and comp_variables[name]['elbow_angle'] != "NA":
					elbow_angle += float(comp_variables[name]['elbow_angle'])
				#Skipped "coupling class" variable
				if 'bolt_pattern_long' in comp_variables[name] and comp_variables[name]['bolt_pattern_long'] != "NA":
					bolt_pattern_long += float(comp_variables[name]['bolt_pattern_long'])
				if 'thread_pitch_1' in comp_variables[name]:
					thread_pitch_names = ['thread_pitch_1', 'thread_pitch_2', 'thread_pitch_3', 'thread_pitch_4']
					for p_name in thread_pitch_names:
						if p_name in comp_variables[name] and comp_variables[name][p_name] != 'NA' and comp_variables[name][p_name] != "9999":
							thread_pitches[p_name] += float(comp_variables[name][p_name])
				if 'groove' in comp_variables[name] and comp_variables[name]['groove'] != "NA":
					if comp_variables[name]['groove'] == "Yes":
						groove_yes += 1
					if comp_variables[name]['groove'] == "No":
						groove_no += 1

		data_merged.set_value(idx, 'num_components', num_components)
		data_merged.set_value(idx, 'total_weight', weight)
		data_merged.set_value(idx, 'orentation_yes', orientation_yes)
		data_merged.set_value(idx, 'orientation_no', orientation_no)
		data_merged.set_value(idx, 'diameter', diameter)
		data_merged.set_value(idx, 'total_nominal_size', total_nominal_size)
		data_merged.set_value(idx, 'thread_pitch', thread_pitch)
		data_merged.set_value(idx, 'adaptor_angle', adaptor_angle)
		data_merged.set_value(idx, 'total_length', total_length)
		data_merged.set_value(idx, 'outside_shape_round', outside_shape_round)
		data_merged.set_value(idx, 'outside_shape_na', outside_shape_na)
		data_merged.set_value(idx, 'outside_shape_hex', outside_shape_hex)
		data_merged.set_value(idx, 'total_base_diameter', total_base_diameter)

		if thread_count == 0:
			data_merged.set_value(idx, 'average_thread_size', total_thread_size)
		else:
			data_merged.set_value(idx, 'average_thread_size', total_thread_size/thread_count)

		for connection_type in connection_type_counter:
			data_merged.set_value(idx, connection_type, connection_type_counter[connection_type])
		data_merged.set_value(idx, 'nut_and_sleeve_length', nut_and_sleeve_length)
		data_merged.set_value(idx, 'thickness', thickness)
		data_merged.set_value(idx, 'mj_plug_class_code', mj_plug_class_code)
		data_merged.set_value(idx, 'base_type_shoulder', base_type_shoulder)
		data_merged.set_value(idx, 'base_type_flatbottom', base_type_flatbottom)
		data_merged.set_value(idx, 'base_type_saddle', base_type_saddle)
		data_merged.set_value(idx, 'hex_size', hex_size)
		data_merged.set_value(idx, 'seat_angle', seat_angle)
		data_merged.set_value(idx, 'total_thread_size', thread_size)
		data_merged.set_value(idx, 'type_boss', type_boss)
		data_merged.set_value(idx, 'type_stud', type_stud)

		for i in end_form_ids:
			data_merged.set_value(idx, i, end_form_ids[i])

		data_merged.set_value(idx, 'intended_nut_pitch', intended_nut_pitch)
		data_merged.set_value(idx, 'bolt_pattern_wide', bolt_pattern_wide)
		data_merged.set_value(idx, 'plug_diameter', plug_diameter)
		data_merged.set_value(idx, 'hex_nut_size', hex_nut_size)
		data_merged.set_value(idx, 'height_over_tube', height_over_tube)
		data_merged.set_value(idx, 'shoulder_diameter', shoulder_diameter)
		data_merged.set_value(idx, 'overall_length', overall_length)
		data_merged.set_value(idx, 'extension_length', extension_length)
		data_merged.set_value(idx, 'intended_nut_thread', intended_nut_thread)
		data_merged.set_value(idx, 'mj_class_code_exists', mj_class_code_exists)
		data_merged.set_value(idx, 'unique_feature_yes', unique_feature_yes)
		data_merged.set_value(idx, 'unique_feature_no', unique_feature_no)
		data_merged.set_value(idx, 'drop_length', drop_length)
		data_merged.set_value(idx, 'elbow_angle', elbow_angle)
		data_merged.set_value(idx, 'bolt_pattern_long', total_base_diameter)

		for i in thread_pitches:
			data_merged.set_value(idx, i, thread_pitches[i])
		data_merged.set_value(idx, 'groove_yes', groove_yes)
		data_merged.set_value(idx, 'groove_no', groove_no)

	print "Counter"
	print counter


	from sets import Set
	values = Set([])
	for entry in comp_variables:
		if 'unique_feature' in comp_variables[entry]:

			values.add(comp_variables[entry]['unique_feature'])
	print values

	


	return data_merged



def extract_train_and_test(train, test):
	#Create total number of supplier quotes variable
	#Counts the number of distinct tube ids for each supplier
	train_s_tid = train[['supplier', 'tube_assembly_id']]
	test_s_tid = test[['supplier', 'tube_assembly_id']]
	concat_s_tid = pd.concat([train_s_tid, test_s_tid])
	grouped = concat_s_tid.groupby('supplier')
	num_suppliers = grouped.tube_assembly_id.nunique()
	df_num_suppliers = pd.DataFrame(num_suppliers)
	df_num_suppliers.columns = ['total_supplier_quotes']
	train = pd.merge(left = train, right = df_num_suppliers, left_on = 'supplier', how = 'left', right_index = True)
	test = pd.merge(left = test, right = df_num_suppliers, left_on = 'supplier', how = 'left', right_index = True)


	#Label encode categorical variables
	labels_to_encode = ['component_id_' + str(x) for x in range(1,9)]
	labels_to_encode.append('supplier')

	for label in labels_to_encode:
		lbl = preprocessing.LabelEncoder()
		lbl.fit(pd.concat([train[label], test[label]]))
		train[label] = lbl.transform(train[label])
		test[label] = lbl.transform(test[label])
	
	#Create average component popularity variable

	#Create price of the similar tube variable - find tubes with the same combo of components and use its average cost
	#as a variable (will want to refine this later)
	#one possible refinement - if there is no exact match, come up with some type of similarity measure that incorporates cost.

	component_ids = ['component_id_' + str(x) for x in range(1,9)]
	quantities = ['quantity_' + str(x) for x in range(1,9)]

	#Build a dictionary of components/quantities as keys, and as values have {tube_id_1: {costs: [list_of_costs]}, tube_id_2: ...}
	components_and_quantities = {}
	from sets import Set

	for idx, row in train.iterrows():
		key = tuple(row[x] for x in component_ids + quantities)
		if key in components_and_quantities:
			if row['tube_assembly_id'] in components_and_quantities[key]:
				components_and_quantities[key][row['tube_assembly_id']]['costs'].append(row['cost'])
				components_and_quantities[key][row['tube_assembly_id']]['quantity'].append(row['quantity'])
				components_and_quantities[key][row['tube_assembly_id']]['suppliers'].add(row['supplier'])

			else:
				components_and_quantities[key][row['tube_assembly_id']] = {'costs': [row['cost']], 'quantity': [row['quantity']], 'suppliers': Set([row['supplier']])}
		else:
			components_and_quantities[key] = {row['tube_assembly_id']: {'costs': [row['cost']], 'quantity': [row['quantity']], 'suppliers': Set([row['supplier']])}}

	for idx, row in test.iterrows():
		key = tuple(row[x] for x in component_ids + quantities)
		if key in components_and_quantities:
			if row['tube_assembly_id'] in components_and_quantities[key]:
				components_and_quantities[key][row['tube_assembly_id']]['quantity'].append(row['quantity'])
				components_and_quantities[key][row['tube_assembly_id']]['suppliers'].add(row['supplier'])
			else:
				components_and_quantities[key][row['tube_assembly_id']] = {'costs': [], 'quantity': [row['quantity']], 'suppliers': Set([row['supplier']])}
		else:
			components_and_quantities[key] = {row['tube_assembly_id']: {'costs': [], 'quantity': [row['quantity']], 'suppliers': Set([row['supplier']])}}


	counter = 0
	for key in components_and_quantities:
		print str(key) + ': ' + str(components_and_quantities[key])
		counter += 1
		if counter >= 5:
			break
	#Save the dict to play around with it
	import pickle
	with open('components_and_quantities.pkl', 'wb') as f:
		pickle.dump(components_and_quantities, f)
	#Fill in the values of average price of tube with similar components. Take value 0 if no other tubes with same component
	#combo. Idea - use median, max, min in addition to average. Also try tracking quantity and making the feature avg(cost/quantity)
	#rather than just avg(cost).
	
	for idx, row in train.iterrows():
		avg_price_of_similar_tubes = 0
		max_price_of_similar_tubes = 0
		min_price_of_similar_tubes = 10000000
		key = tuple(row[x] for x in component_ids + quantities)
		
		'''
		if len(components_and_quantities[key]) > 1:
			total = 0
			count = 0
			for tube_id in components_and_quantities[key]:
				if tube_id != row['tube_assembly_id']:
					total += sum(components_and_quantities[key][tube_id]['costs'])
					count += len(components_and_quantities[key][tube_id]['costs'])
					if components_and_quantities[key][tube_id]['costs']:
						running_max = max(components_and_quantities[key][tube_id]['costs'])
						running_min = min(components_and_quantities[key][tube_id]['costs'])
						if running_max > max_price_of_similar_tubes:
							max_price_of_similar_tubes = running_max
						if running_min < min_price_of_similar_tubes:
							min_price_of_similar_tubes = running_min

			if count != 0:
				avg_price_of_similar_tubes = float(total)/float(count)
			adj_avg_price_of_similar_tubes = avg_price_of_similar_tubes - np.log(row['quantity'])
		train.set_value(idx, "avg_price_of_similar_tubes", avg_price_of_similar_tubes)
		train.set_value(idx, "max_price_of_similar_tubes", max_price_of_similar_tubes)
		if min_price_of_similar_tubes == 10000000:
			min_price_of_similar_tubes = 0
		train.set_value(idx, "min_price_of_similar_tubes", min_price_of_similar_tubes)
		train.set_value(idx, "adj_avg_price_of_similar_tubes", adj_avg_price_of_similar_tubes)
		'''

		num_tubes_with_same_component_list = len(components_and_quantities[key])
		train.set_value(idx, "num_tubes_with_same_component_list", num_tubes_with_same_component_list)
		
		#num_suppliers_with_same_component_list = sum(len(components_and_quantities[key][tube_id]['suppliers']) for tube_id in components_and_quantities[key])
		num_suppliers_with_same_component_list = len(reduce(lambda x,y: x.union(y), [components_and_quantities[key][tube_id]['suppliers'] for tube_id in components_and_quantities[key]]))
		train.set_value(idx, "num_suppliers_with_same_component_list", num_suppliers_with_same_component_list)

		#Other idea - just look at the price of a tube with a "nearby" tube name. e.g. you are looking at TA-02796
		#and then use the price of TA-02797 or TA-02795 (if they exist with a cost) - if they don't exist, just set variable to 0.
		#Code below extracts the minimum 
		#Possible refinement - make adjacent_cost the cost with the closest quantity to the record we are looking at
		tube_assembly_id = row['tube_assembly_id']
		adjacent_tube_assembly_ids = get_adjacent_tube_assembly_ids(tube_assembly_id)
		min_adjacent_cost = 0
		max_adjacent_cost = 0
		average_adjacent_cost = 0
		for adjacent_tube in adjacent_tube_assembly_ids:
			if adjacent_tube in components_and_quantities[key] and components_and_quantities[key][adjacent_tube]['costs']:
				min_adjacent_cost = min(components_and_quantities[key][adjacent_tube]['costs'])
				max_adjacent_cost = max(components_and_quantities[key][adjacent_tube]['costs'])
				average_adjacent_cost = sum(components_and_quantities[key][adjacent_tube]['costs'])/float(len(components_and_quantities[key][adjacent_tube]['costs']))

				break
		train.set_value(idx, "min_adjacent_cost", min_adjacent_cost)
		train.set_value(idx, "max_adjacent_cost", max_adjacent_cost)
		train.set_value(idx, "average_adjacent_cost", average_adjacent_cost)



	for idx, row in test.iterrows():
		avg_price_of_similar_tubes = 0
		max_price_of_similar_tubes = 0
		min_price_of_similar_tubes = 10000000
		key = tuple(row[x] for x in component_ids + quantities)
		
		'''
		if key in components_and_quantities:
			total = 0
			count = 0
			for tube_id in components_and_quantities[key]:
				total += sum(components_and_quantities[key][tube_id]['costs'])
				count += len(components_and_quantities[key][tube_id]['costs'])
				if components_and_quantities[key][tube_id]['costs']:
					running_max = max(components_and_quantities[key][tube_id]['costs'])
					running_min = min(components_and_quantities[key][tube_id]['costs'])
					if running_max > max_price_of_similar_tubes:
						max_price_of_similar_tubes = running_max
					if running_min < min_price_of_similar_tubes:
						min_price_of_similar_tubes = running_min
			
			if count != 0:
				avg_price_of_similar_tubes = float(total)/float(count)
				
			adj_avg_price_of_similar_tubes = avg_price_of_similar_tubes - np.log(row['quantity'])
		test.set_value(idx, "avg_price_of_similar_tubes", avg_price_of_similar_tubes)
		test.set_value(idx, "max_price_of_similar_tubes", max_price_of_similar_tubes)
		if min_price_of_similar_tubes == 10000000:
			min_price_of_similar_tubes = 0
		test.set_value(idx, "min_price_of_similar_tubes", min_price_of_similar_tubes)
		test.set_value(idx, "adj_avg_price_of_similar_tubes", adj_avg_price_of_similar_tubes)
		'''

		num_tubes_with_same_component_list = len(components_and_quantities[key])
		test.set_value(idx, "num_tubes_with_same_component_list", num_tubes_with_same_component_list)

		#num_suppliers_with_same_component_list = sum(len(components_and_quantities[key][tube_id]['suppliers']) for tube_id in components_and_quantities[key])
		num_suppliers_with_same_component_list = len(reduce(lambda x,y: x.union(y), [components_and_quantities[key][tube_id]['suppliers'] for tube_id in components_and_quantities[key]]))
		test.set_value(idx, "num_suppliers_with_same_component_list", num_suppliers_with_same_component_list)
		#Other idea - just look at the price of a tube with a "nearby" tube name. e.g. you are looking at TA-02796
		#and then use the price of TA-02797 or TA-02795 (if they exist with a cost) - if they don't exist, just set variable to 0.
		#Code below extracts the minimum 
		tube_assembly_id = row['tube_assembly_id']
		adjacent_tube_assembly_ids = get_adjacent_tube_assembly_ids(tube_assembly_id)
		min_adjacent_cost = 0
		max_adjacent_cost = 0
		average_adjacent_cost = 0
		for adjacent_tube in adjacent_tube_assembly_ids:
			if adjacent_tube in components_and_quantities[key] and components_and_quantities[key][adjacent_tube]['costs']:
				min_adjacent_cost = min(components_and_quantities[key][adjacent_tube]['costs'])
				max_adjacent_cost = max(components_and_quantities[key][adjacent_tube]['costs'])
				average_adjacent_cost = sum(components_and_quantities[key][adjacent_tube]['costs'])/float(len(components_and_quantities[key][adjacent_tube]['costs']))
				break
		test.set_value(idx, "min_adjacent_cost", min_adjacent_cost)
		test.set_value(idx, "max_adjacent_cost", max_adjacent_cost)
		test.set_value(idx, "average_adjacent_cost", average_adjacent_cost)

	suppliers_and_quote_dates = pd.concat([test[['supplier', 'quote_year', 'quote_month']], train[['supplier', 'quote_year', 'quote_month']]])
	grouped = suppliers_and_quote_dates.groupby('supplier')
	min_years = grouped.aggregate(np.min)
	min_years.columns = ['min_quote_year', 'min_quote_month']
	train = pd.merge(left = train, right = min_years, left_on = 'supplier', how = 'left', right_index = True)
	test = pd.merge(left = test, right = min_years, left_on = 'supplier', how = 'left', right_index = True)

	train['length_of_supplier_relationship'] = (train['quote_year'] - train['min_quote_year']) * 12 + train['quote_month'] - train['min_quote_month']
	test['length_of_supplier_relationship'] = (test['quote_year'] - test['min_quote_year']) * 12 + test['quote_month'] - test['min_quote_month']
	

	quantities_to_agg = pd.concat([test[['tube_assembly_id', 'quantity']], train[['tube_assembly_id', 'quantity']]])
	grouped = quantities_to_agg.groupby('tube_assembly_id')
	min_quantity = grouped.aggregate(np.min)
	max_quantity = grouped.aggregate(np.max)

	min_quantity.columns = ['min_quantity']
	max_quantity.columns = ['max_quantity']

	train = pd.merge(left = train, right = min_quantity, left_on = 'tube_assembly_id', how = 'left', right_index = True)
	test = pd.merge(left = test, right = min_quantity, left_on = 'tube_assembly_id', how = 'left', right_index = True)

	train = pd.merge(left = train, right = max_quantity, left_on = 'tube_assembly_id', how = 'left', right_index = True)
	test = pd.merge(left = test, right = max_quantity, left_on = 'tube_assembly_id', how = 'left', right_index = True)

	return (train, test)


if __name__ == '__main__':
	train = pd.read_csv('competition_data/train_set.csv')
	test = pd.read_csv('competition_data/test_set.csv')

	#Want to train model (and develop relevant features) using log(1 + x), as it is
	#better suited for the RMSLE evaluation metric.
	train['cost'] = np.log1p(train['cost'])
	train = extract(train)
	test = extract(test)

	#Perform extraction that relies on aggregating data across train and test sets
	(train, test) = extract_train_and_test(train, test)

	train.to_csv('extracted_train.csv', index=False)
	test.to_csv('extracted_test.csv', index=False)

	#Dump the extracted data for use in modelling.py
	pickle.dump(train, open('extracted_train.pkl', 'wb'))
	pickle.dump(test, open('extracted_test.pkl', 'wb'))