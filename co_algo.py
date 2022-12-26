#!/usr/bin/python
import math
from core import co_logger
from scipy.signal import find_peaks

class HistoryWindow():
	def __init__(self, coordinates, window_size):
		self.Coordinates	= coordinates
		self.First			= 0
		self.End			= 0
		self.WindowSize 	= window_size

	def Curr(self):
		x   = self.Coordinates["x"][self.First: self.End]
		y   = self.Coordinates["y"][self.First: self.End]
		idx = self.Coordinates["idx"][self.First: self.End]

		return {
			"x": x,
			"y": y,
			"idx": idx,
			"count": len(x)
		}
	
	def Next(self):
		if self.End < self.WindowSize - 1:
			self.End += 1
			return None
		
		if (len(self.Coordinates["x"]) <= self.End):
			return None

		self.First  += 1
		self.End    += 1

		return self.Curr()
	
	def Prev(self):
		if self.First == 0:
			return None
		
		self.First	-= 1
		self.End	-= 1

		return self.Curr()

class AlgoMath():
	def __init__(self):
		pass
	
	def FindBufferMaxMin(self, buffer):
		pmax = 0		
		pmin = 0
		if len(buffer) > 0:
			pmin = buffer[0]
			for item in buffer:
				if pmax < item:
					pmax = item
				if pmin > item:
					pmin = item
		return pmin, pmax

	def CreateHistogram(self, buffer, bin_size):
		ret_hist_buffer_y = []
		ret_hist_buffer_x = []
		freq = 1
		try:
			if len(buffer) > 0:
				# Find min and max for this buffer
				pmin, pmax = self.FindBufferMaxMin(buffer)
				# Calculate freq
				freq = (float(pmax) - float(pmin)) / float(bin_size)
				if freq == 0:
					return 0, [pmin], [pmax]
				# Generate x scale
				ret_hist_buffer_x = [(x * freq) + pmin for x in range(0, bin_size)]
				ret_hist_buffer_y = [0] * bin_size
				# Generate y scale
				for sample in buffer:
					index = int((float(sample) - float(pmin)) / freq)
					if index == 25:
						index = 24
					#print(index, sample, freq, pmin, pmax)
					ret_hist_buffer_y[index] += 1
		except Exception as e:
			print("Histograme exception {0}".format(e))
			return 1, [], []
		return 0, ret_hist_buffer_y, ret_hist_buffer_x
	
	def CalculatePercentile(self, low, high, histogram):
		low_perc  			= 0
		low_perc_found  	= False

		mid_perc 			= 0
		mid_perc_found 		= False

		high_perc 			= 0
		high_perc_found 	= False

		pmin 				= 0
		pmin_found 			= False
	
		pmax 				= 0
		pmax_found 			= False

		perc_integral 		= 0.0
		hist_sum 			= 0.0

		hist_len 			= len(histogram)

		for sample in histogram:
			hist_sum += sample

		# TODO - use liniar interpulation
		for idx, sample in enumerate(histogram):
			perc_integral += sample
			if low_perc_found is False:
				if (perc_integral / hist_sum) > low:
					low_perc_found = True
					low_perc = idx
			if high_perc_found is False:
				if (perc_integral / hist_sum) > high:
					high_perc_found = True
					high_perc = idx
			if mid_perc_found is False:
				if (perc_integral / hist_sum) >= 0.5:
					mid_perc_found = True
					mid_perc = idx
			if pmin_found is False:
				if sample > 0:
					pmin_found = True
					pmin = idx
			if pmax_found is False:
				if histogram[(hist_len - 1) - idx] > 0:
					pmax_found = True
					pmax = (hist_len - 1) - idx
		
		return pmin, low_perc, mid_perc, high_perc, pmax
	
	def FindPeaks(self, x, y, width, height):
		positive = []
		negative = []
		for value in y:
			if value > 0:
				positive.append(value)
				negative.append(0)
			elif value < 0:
				negative.append(0-value)
				positive.append(0)
			else:
				positive.append(0)
				negative.append(0)

		peaks_data = [0]*len(x)

		if height <= 0:
			height = None
		if width <= 0:
			width = None

		pos_peaks, pos_ = find_peaks(positive, height=height, width=width)
		neg_peaks, neg_ = find_peaks(negative, height=height, width=width)

		pos_peaks_arr = pos_peaks.tolist()
		neg_peaks_arr = neg_peaks.tolist()

		for idx in pos_peaks_arr:
			peaks_data[idx] = 1
		
		for idx in neg_peaks_arr:
			peaks_data[idx] = -1

		return peaks_data

	def CalculateRegressionRows(self, x, y):
		if len(x) != len(y):
			return None, None
		
		avg_x = 0
		avg_y = 0
		x_dist_2_sum = 0
		y_dist_2_sum = 0

		# Calculate avgs
		for idx, value in enumerate(x):
			avg_x += value
			avg_y += y[idx]
			
		avg_x = (avg_x) / (len(x))
		avg_y = (avg_y) / (len(y))

		for idx, value in enumerate(x):
			x_dist = value - avg_x
			y_dist = y[idx] - avg_y

			x_dist_2 = x_dist * x_dist
			y_dist_2 = x_dist * y_dist

			x_dist_2_sum += x_dist_2
			y_dist_2_sum += y_dist_2
		
		if x_dist_2_sum <= 0:
			return 0, 0
		
		slope = (y_dist_2_sum) / (x_dist_2_sum)
		b = avg_y - slope * avg_x

		return slope, b
	
	def CalculateRegression(self, coordinates):
		avg_x = 0
		avg_y = 0
		x_dist_2_sum = 0
		y_dist_2_sum = 0
		# Calculate avgs
		for sample in coordinates:
			avg_x += sample["x"]
			avg_y += sample["y"]
			
		avg_x = (avg_x) / (len(coordinates))
		avg_y = (avg_y) / (len(coordinates))

		for sample in coordinates:
			sample["x_dist"] = sample["x"] - avg_x
			sample["y_dist"] = sample["y"] - avg_y

			sample["x_dist_2"] = sample["x_dist"] * sample["x_dist"]
			sample["y_dist_2"] = sample["x_dist"] * sample["y_dist"]

			x_dist_2_sum += sample["x_dist_2"]
			y_dist_2_sum += sample["y_dist_2"]
		
		if x_dist_2_sum <= 0:
			return 0, 0
		
		slope = (y_dist_2_sum) / (x_dist_2_sum)
		b = avg_y - slope * avg_x

		return slope, b
		
	def RValue(self, coordinates, slope, b):
		avg_y = 0
		y_dist_2_sum = 0
		estimated_y_dist_2_sum = 0
		# Calculate avgs
		for sample in coordinates:
			avg_y += sample["y"]
		avg_y = float(avg_y) / float(len(coordinates))

		for sample in coordinates:
			sample["y_dist"] = sample["y"] - avg_y
			sample["y_dist_2"] = sample["y_dist"] * sample["y_dist"]
			sample["estimated_y"] = sample["x"] * slope + b
			sample["estimated_y_dist"] = sample["estimated_y"] - avg_y
			sample["estimated_y_dist_2"] = sample["estimated_y_dist"] * sample["estimated_y_dist"]
			y_dist_2_sum += sample["y_dist_2"]
			estimated_y_dist_2_sum += sample["estimated_y_dist_2"]
		
		if float(y_dist_2_sum) <= 0.0:
			return 0.0
		
		r = float(estimated_y_dist_2_sum) / float(y_dist_2_sum)
		return r
	
	def Variance(self, data, ddof=0):
		n = len(data)
		mean = sum(data) / n
		return sum((x - mean) ** 2 for x in data) / (n - ddof)

	def Stdev(self, data):
		var = self.Variance(data)
		std_dev = math.sqrt(var)
		return std_dev

	def ArrayTemplateFinder(self, src, pattern):
		pattern_len = len(pattern)
		src_len = len(src)

		if pattern_len > src_len:
			return []
		
		found_indexes = []
		for idx in range(src_len-pattern_len):
			if pattern == src[idx:idx+(pattern_len)]:
				found_indexes.append(idx)
			
		return found_indexes

	def MovingAVGNoBufferCreateContext(self, window_size):
		return {
			"avg": 0.0,
			"window_size": window_size
		}

	def MovingAVGNoBuffer(self, ctx, sample):
		if ctx["avg"] > 0:
			ctx["avg"] = ((1.0 - (1.0 / (float)(ctx["window_size"]))) * ctx["avg"]) + (1.0 / (float)(ctx["window_size"])) * sample
		else:
			ctx["avg"] = sample
		
		return ctx["avg"]