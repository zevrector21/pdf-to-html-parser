import pdfplumber, PyPDF2
import csv, json
import os, sys
import pdb


class PDFParser:
	image_index = 0
	extension_type = 'jpeg'
	resolution = 150
	delta = 30
	font = 'p'

	def __init__(self, file_name):
		# self.file_name = input('File Name:')
		# if self.file_name == '':
		# self.file_name = 'input'
		self.file_name = file_name
		self.directory = self.file_name
		if not os.path.isdir(self.directory):
			os.makedirs(self.directory)
		if not os.path.isdir(f'{self.directory}/images'):
			os.makedirs(f'{self.directory}/images')
		self.parse_content()

	# parse pdf content
	def parse_content(self):
		try:
			pdb.set_trace()
			py_pdf = PyPDF2.PdfFileReader(open(f'{self.file_name}.pdf', 'rb'))
			pdf = pdfplumber.open(f'{self.file_name}.pdf')
			self.file_name = self.file_name.replace(' ', '_')
			page_length = len(pdf.pages)
			for idx in range(0, page_length):
				items = []
				try:
					page_content = py_pdf.getPage(idx).extractText().encode('ascii','ignore').decode('utf-8-sig')
					self.page = pdf.pages[idx]
					self.all_words = self.page.extract_words()
					self.images = self.page.images
					self.page_height = self.page.height
					self.chars = self.page.chars
					content = self.page.extract_text()
					if page_content:
						lines = self.eliminate_space(page_content.split('\n'))
						end_marks = ['.', '!', ':']
						sentence = []
						for line in lines:
							words = self.eliminate_space(line.split(' '))
							for word in words:
								sentence.append(word)
								title_word = self.get_word_with_pos(word, ' '.join(sentence), True)
								if title_word:
									font_size = self.get_font_of_word(title_word)
									if font_size > 20: self.font = 'h4'
									if font_size > 24: self.font = 'h3'
									if font_size > 28: self.font = 'h2'
									if font_size > 32: self.font = 'h1'
								if word[-1] in end_marks and word != 'Dr.':
									if len(sentence) > 1:
										items.append({
											'value'	: ' '.join(sentence),
											'tag': self.font
										})
										self.font = 'p'
									sentence = []
								cursor_word = self.get_word_with_pos(word, ' '.join(sentence))
								if cursor_word:
									images = self.get_image_around(cursor_word)
									if images != []:
										for image in images:
											items.append({
												'value': image['value'],
												'tag': 'img',
												'full': image['full']
											})
						items.append({
							'value'	: ' '.join(sentence),
							'tag': self.font
						})
					# for image in self.images:
					# 	s_image = self.save_image(image)
					# 	items.append({
					# 		'value': s_image['value'],
					# 		'tag': 'img',
					# 		'full': s_image['full']
					# 	})
					self.save_as_html(items, idx+1)
				except Exception as e:
					print(idx, e)
			print('PDF is parsed successfully !!!')
		except Exception as e:
			print('Oops, something went wrong in the PDF file.', e)

	def get_font_of_word(self, word):
		font_size = 0
		for char in self.chars:
			if char['x0'] == word['x0'] and char['top'] == word['top']:
				font_size = float(char['size'])
				break
		return font_size

	def validate(self, item): 
	    if item == None:
	        item = ''
	    if type(item) == int or type(item) == float:
	        item = str(item)
	    if type(item) == list:
	        item = ' '.join(item)
	    return item.strip()
	
	def eliminate_space(self, items):
		rets = []
		for item in items:
			item = self.validate(item)
			if item == '':
				continue
			rets.append(item)
		return rets

	def get_word_with_pos(self, word, sentence, title=False):
		all_words = self.all_words
		for idx, a_word in enumerate(all_words):
			if a_word['text'] == word:				
				try:
					sub_sentence = f'{all_words[idx-1]["text"]} {word}'
					if title:
						# sub_sentence = f'{all_words[idx-2]["text"]} {all_words[idx-1]["text"]} {word}'
						sub_sentence = f' {all_words[idx-1]["text"]} {word}'
					if sub_sentence in sentence:
						self.all_words.pop(idx)
						return a_word
				except Exception as e:
					pass
		return None

	def get_image_around(self, word):
		images = self.images
		rets = []
		for idx, image in enumerate(images):
			x_diff = (word['x1'] + word['x0'])/2
			y_b_diff = abs(self.page_height - image['y1'] - word['bottom'])
			y_t_diff = abs(self.page_height - image['y0'] - word['top'])
			is_inside = word['bottom'] > (self.page_height - image['y1']) and word['bottom'] < (self.page_height - image['y0'])
			if  x_diff > image['x0'] and x_diff < image['x1'] and (y_b_diff < self.delta or y_t_diff < self.delta or is_inside):
				s_image = self.save_image(image)
				self.images.pop(idx)
				rets.append({
					'value': s_image['value'],
					'full': s_image['full']
				})
				return self.get_image_next(image, rets)
		return rets

	def get_image_next(self, cur_image, rets):
		images = self.images
		for idx, image in enumerate(images):
			x_c_diff = (cur_image['x1'] + cur_image['x0'])/2
			x_n_diff = (image['x1'] + image['x0'])/2
			y_t_diff = abs(image['y1'] - cur_image['y0'])
			y_b_diff = abs(image['y0'] - cur_image['y1'])
			if  ((x_c_diff > image['x0'] and x_c_diff < image['x1']) or (x_n_diff > cur_image['x0'] and x_n_diff < cur_image['x1'])) and (y_t_diff < self.delta or y_b_diff < self.delta):
				s_image = self.save_image(image)
				self.images.pop(idx)
				rets.append({
					'value': s_image['value'],
					'full': s_image['full']
				})
				return self.get_image_next(image, rets)
		return rets

	def save_image(self, image):
		image_bbox = (image['x0'], self.page_height - image['y1'], image['x1'], self.page_height - image['y0'])
		image_name = f'images/{self.file_name}_{self.image_index}.{self.extension_type}'
		cropped_page = self.page.crop(image_bbox)
		image_obj = cropped_page.to_image(resolution=self.resolution)
		# if not os.path.exists(image_name):
		image_obj.save(f'{self.directory}/{image_name}')
		width = image['x1'] - image['x0']
		full = False
		self.image_index += 1
		return {
			'value':image_name,
			'full': full
		}

	def save_as_html(self, items, idx):
		with open(f'{self.directory}/{self.file_name}_{idx}.html', mode='w', encoding='utf-8-sig') as output:
			begins = [
				'<html>',
				'<head>'
				f'<title>{self.file_name}</title>',
				'</head>',
				'<body style="display: flex; font-family: arial">',
				'<div style="width: 60%;margin: auto; display: flex; flex-direction: column;">',
				''
			]
			output.write('\n'.join(begins))
			for item in items:
				line = self.wrap_with_tag(item)
				output.write(line)
			ends = [
				'</div>'
				'</body>',
				'</html>'
			]
			output.write('\n'.join(ends))

	def wrap_with_tag(self, item):
		words = item["value"].split(' ')
		rets = []
		for word in words:
			if 'http://'in word or 'https://' in word:
				word = f'<a href="{word}" target="blank">{word}</a>'
			rets.append(word)
		rets = ' '.join(rets)
		if item['tag'] == 'img':
			if item['full']:
				line = f'<{item["tag"]} src={rets} style="margin: 5px auto; width: 100%"/>'
			else:
				line = f'<{item["tag"]} src={rets} style="margin: 5px auto; max-width: 100%"/>'
		else:
			line = f'<{item["tag"]}>{rets}</{item["tag"]}>'		
		line += '\n'
		return line

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('File name is required')
		exit(0)
	PDFParser(sys.argv[1]) # pass filename
