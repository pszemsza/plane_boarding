from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, IntEnum

import numpy as np
import itertools


SPEED_MOVE = 2
SPEED_SEATING = 3
SPEED_STOW_BAGGAGE = 3

class State(IntEnum):
	UNDEFINED = 0
	BOARDING_QUEUE = 1
	MOVE_WAIT = 2
	MOVE_TO_ROW = 3
	STOW_BAGGAGE = 4
	WAIT_TO_SEAT = 5
	SEATING = 6
	VACATING_ROW = 7
	RESEATING = 8
	SEATED = 9


class BoardingZones(Enum):
	RANDOM = 0
	BACK_TO_FRONT_BY_ROWS = 1
	BACK_TO_FRONT_BY_ROWS_WINDOW_TO_AISLE = 2
	BACK_TO_FRONT_2_ZONES = 3
	BACK_TO_FRONT_3_ZONES = 4
	BACK_TO_FRONT_4_ZONES = 5
	FRONT_TO_BACK_BY_ROWS = 6
	FRONT_TO_BACK_BY_ROWS_WINDOW_TO_AISLE = 7
	WINDOW_TO_AISLE = 8
	WINDOW_TO_AISLE_BACK_TO_FRONT_ONE_PERSON_PER_ROW = 9
	STEFFEN = 10
	STEFFEN_MODIFIED = 11
	BACK_TO_FRONT_BY_ROWS_WITH_SPACING = 12
	

# Describes state of the vacating row (i.e. when someone needs to vacate a row to let another person pass through).
# This requires coordination of multiple passengers, so we do this in a centralized way.
@dataclass
class RowVacating:
	passengers: list[int]        # Ordered from the nearest to the aisle towards the window
	row_cleared: bool = False
	next_action_t: int = 0       # Timestamp at which there will the next change


@dataclass
class Passenger:
	seat_row: int                      # Assigned row
	seat: int                          # Assigned seat number (e.g. 1-3 for places on the right, negative numbers for places to the left)
	has_baggage: bool = True           
	state: State = State.UNDEFINED
	x: int = None                      # Current position
	y: int = None                      # Current position
	is_seated: bool = False
	next_action_t: int = 0             # Timestamp of the next (potential) state change

	
class Simulation:
	def __init__(self, dummy_rows=2, quiet_mode = True):
		self.dummy_rows = dummy_rows       # We add dummy rows to have some space before the actual seats appear.
		self.passengers = []
		self.t = 0
		self.history = defaultdict(list)
		self.history_baggage = []
		self.row_vacating = {}
		self.boarding_zones = BoardingZones.RANDOM
		self.quiet_mode = quiet_mode
		self.reset_stats()

	def set_custom_aircraft(self, n_rows, n_seats_left=2, n_seats_right=2):
		self.n_rows = n_rows
		self.n_seats_left = n_seats_left
		self.n_seats_right = n_seats_right

	def set_passengers_number(self, n):
		self.n_passengers = n

	def set_passengers_proportion(self, proportion):
		capacity = self.n_rows * (self.n_seats_left + self.n_seats_right)
		self.n_passengers = int(proportion * capacity)

	def set_boarding_zones(self, boarding_zones):
		self.boarding_zones = boarding_zones

	def reset_stats(self):
		self.boarding_time = []

	def print(self):
		for i in range(self.n_rows+self.dummy_rows):
			row = list(self.side_left[i, :][::-1]) + ['|', '[' + str(self.baggage_bin[i][0]) + ']', self.aisle[i], '[' + str(self.baggage_bin[i][1]) + ']', '|'] + list(self.side_right[i, :])
			if i in self.row_vacating:
				row.append('vacating')
				row.append(self.row_vacating[i].passengers)
				row.append(self.row_vacating[i].next_action_t)
			self.print_info(row)

	def print_boarding_order(self):
		for i in range(self.dummy_rows, self.n_rows+self.dummy_rows):
			row = list(self.boarding_order_left[i, :][::-1]) + [' '] + list(self.boarding_order_right[i, :])
			print(row)

	def reset(self):
		self.t = 0
		self.history = defaultdict(list)
		self.history_baggage = []
		self.row_vacating = {}

		self.side_left = np.zeros((self.n_rows+self.dummy_rows, self.n_seats_left), dtype=int)
		self.side_right = np.zeros((self.n_rows+self.dummy_rows, self.n_seats_right), dtype=int)
		self.aisle = np.zeros(self.n_rows+self.dummy_rows, dtype=int)
		self.baggage_bin = np.zeros((self.n_rows+self.dummy_rows, 2), dtype=int)

		self.boarding_order_left = np.zeros((self.n_rows+self.dummy_rows, self.n_seats_left), dtype=int)
		self.boarding_order_right = np.zeros((self.n_rows+self.dummy_rows, self.n_seats_right), dtype=int)

		self.randomize_passengers()

	def randomize_passengers(self):
		seat_cols = set(range(-self.n_seats_left, self.n_seats_right+1)) - {0}   # Possible seats
		seat_rows = range(self.dummy_rows, self.n_rows+self.dummy_rows)          # Possible rows

		# 1. Get all seats on the plane
		#    Every seat is described by a 3-element list: [row, column, boarding zone]
		#    Initially we zet all zones to 0, and we set the actual values later
		# 2. Randomly select seat indices for every passenger
		# 3. Create seat's list (i-th seat corresponds to the )
		all_seats = list(list(x) for x in itertools.product(seat_rows, seat_cols, [0]))
		selected_seats_ind = np.random.choice(len(all_seats), size=self.n_passengers, replace=False)
		selected_seats = [all_seats[seat_ind] for seat_ind in selected_seats_ind]

		# Here we iterate over all seats and set the correct boarding zone.

		if self.boarding_zones == BoardingZones.BACK_TO_FRONT_BY_ROWS:
			for seat in selected_seats:
				seat[2] = seat[0] - self.dummy_rows

		if self.boarding_zones == BoardingZones.FRONT_TO_BACK_BY_ROWS:
			for seat in selected_seats:
				seat[2] = self.n_rows - seat[0] + self.dummy_rows

		# Start with the last row and move towards to the front, with the window-to-aisle order per row.
		if self.boarding_zones == BoardingZones.BACK_TO_FRONT_BY_ROWS_WINDOW_TO_AISLE:
			seat_zones = max(self.n_seats_left, self.n_seats_right)
			for seat in selected_seats:
				seat[2] = (seat[0] - self.dummy_rows) * seat_zones + abs(seat[1]) - 1

		if self.boarding_zones == BoardingZones.FRONT_TO_BACK_BY_ROWS_WINDOW_TO_AISLE:
			seat_zones = max(self.n_seats_left, self.n_seats_right)
			for seat in selected_seats:
				seat[2] = (self.n_rows - seat[0] + self.dummy_rows) * seat_zones + abs(seat[1]) - 1

		# First window seats, then seats next to them, and so on, with aisle seats at the end.
		if self.boarding_zones == BoardingZones.WINDOW_TO_AISLE:
			for seat in selected_seats:
				seat[2] = abs(seat[1]) - 1

		if self.boarding_zones == BoardingZones.BACK_TO_FRONT_BY_ROWS_WITH_SPACING:
			# It is easier to calculate the row order with 0 being the fastest, hence we need to reverse it at the end.
			max_ind = 2 * (self.n_rows + self.dummy_rows) - 1
			for seat in selected_seats:
				row_ind = self.dummy_rows + self.n_rows - seat[0] - 1   # row index, counting from the back
				row_order = 2 * (row_ind % 3) + (1 if seat[1] > 0 else 0)  # row order in each batch of 3 rows
				ind = row_order * (self.n_rows+2)/3
				ind += row_ind / 3   # the closer the row to the front, the larger the delay
				seat[2] = max_ind - ind
		
		if self.boarding_zones == BoardingZones.STEFFEN:
			for seat in selected_seats:
				seat_zones = max(self.n_seats_left, self.n_seats_right)
				ind = seat[0] / 2
				if (self.dummy_rows + self.n_rows - seat[0]) % 2:
					ind = seat[0] / 2 + self.n_rows					

				col_ind = 4 * (abs(seat[1]) - 1)
				if seat[1] > 0:
					col_ind += 1

				ind += col_ind * self.n_rows / 2
				seat[2] = ind

		if self.boarding_zones == BoardingZones.STEFFEN_MODIFIED:
			for seat in selected_seats:
				ind = 2 * ((self.dummy_rows + self.n_rows - seat[0]) % 2)
				if seat[1] > 0:
					ind += 1
				seat[2] = ind

		# Use batches of exactly one person from each row (starting from window seats and moving towards the aisle).
		if self.boarding_zones == BoardingZones.WINDOW_TO_AISLE_BACK_TO_FRONT_ONE_PERSON_PER_ROW:
			seats_on_right = self.n_seats_right * self.n_rows
			for seat in selected_seats:
				if seat[1] > 0:
					seat[2] = (seat[1]-1) * self.n_rows + seat[0] - self.dummy_rows
				else:
					seat[2] = seats_on_right + (abs(seat[1])-1) * self.n_rows + seat[0] - self.dummy_rows
			

		if self.boarding_zones in [BoardingZones.BACK_TO_FRONT_2_ZONES, BoardingZones.BACK_TO_FRONT_3_ZONES, BoardingZones.BACK_TO_FRONT_4_ZONES]:
			zones = 2
			if self.boarding_zones == BoardingZones.BACK_TO_FRONT_3_ZONES:
				zones = 3
			if self.boarding_zones == BoardingZones.BACK_TO_FRONT_4_ZONES:
				zones = 4
			bins = [self.dummy_rows - 1 + 1.0*self.n_rows*i/zones for i in range(1, zones+1)]
			for seat in selected_seats:
				for i in range(len(bins)):
					if seat[0] <= bins[i]:
						seat[2] = i
						break

		# Having zones assigned to the seats, we must make sure to sort passengers accordingly.
		# sort() is guaranteed to be stable, so we can just the seats by the zone number.
		selected_seats.sort(key=lambda x: x[2], reverse=True)

		# Create passengers
 		# Add a dummy element so that passengers are 1-indexed. We do this so that 0 in self.side_left etc. represents "no passenger"
		self.passengers = [None]  
		for seat in selected_seats:
			self.passengers.append(Passenger(seat_row=seat[0], seat=seat[1], state=State.BOARDING_QUEUE))

			# Save boarding order (not really needed for the simulation, but useful for debugging and visualization)
			if seat[1] > 0:
				self.boarding_order_right[seat[0], seat[1]-1] = seat[2]
			else:
				self.boarding_order_left[seat[0], -seat[1]-1] = seat[2]
	
	# Checks whether seat [row, column] is empty, and there is no one sitting between the seat and the aisle.
	def is_seat_accessible(self, row, seat):
		if seat > 0:
			return not np.any(self.side_right[row, :seat])
		return not np.any(self.side_left[row, :-seat])
	
	# A new passenger tries to seat, but there is someone standing (well, seating) in the way.
	# Returns time needed to fully vacate the row.
	def vacate_row(self, new_passenger_id, row, seat):
		passengers = []
		waiting_time = 0

		def process_passenger(pid, passengers):
			p = self.passengers[pid]
			p.state = State.VACATING_ROW
			time_to_vacate = abs(p.seat) * SPEED_SEATING
			p.next_action_t = self.t + time_to_vacate
			self.history[pid].append([self.t, p.x, p.y, int(State.VACATING_ROW)])
			passengers.append(pid)
			return time_to_vacate
			
		if seat > 0:
			for i in range(seat-1):
				pid = self.side_right[row, i]
				if pid:
					waiting_time = process_passenger(pid, passengers)
		else:
			for i in range(-seat-1):
				pid = self.side_left[row, i]
				if pid:
					waiting_time = process_passenger(pid, passengers)

		passengers.append(new_passenger_id)
		vacate_entry = RowVacating(passengers=passengers, next_action_t=self.t+waiting_time)
		self.row_vacating[row] = vacate_entry
		return waiting_time

	def print_info(self, *args):
		if not self.quiet_mode:
			print(*args)

	# Run multiple simulations
	def run_multiple(self, n):
		self.reset_stats()
		for i in range(n):
			self.run()

	# Run a single simulation
	def run(self):
		self.reset()
		while True:
			self.print_info(f'\n*** Step {self.t}')
			finished = self.step()
			if not self.quiet_mode:
				self.print()

			if finished:
				break
			self.t += 1
		
		# Update stats
		self.boarding_time.append(self.t)

	# Process a single animation step.
	def step(self):
		# First processed rows that are vacated.
		vacating_finished = []
		for row, entry in self.row_vacating.items():
			if entry.next_action_t > self.t: continue

			if len(entry.passengers) > 0:
				# If there are still passengers waiting, make the next in line to seat.
				pid = entry.passengers[-1]
				self.passengers[pid].state = State.SEATING
				self.passengers[pid].next_action_t = self.t + SPEED_SEATING
				self.history[pid].append([self.t, 0, row, int(State.VACATING_ROW)])

				entry.next_action_t = self.t + SPEED_SEATING
				entry.passengers.pop()
			else:
				# No more passengers, so mark as completed.
				vacating_finished.append(row)
		
		# Clean vacated rows: mark the aisle as empty in that row, and remove row vacating structure. 
		for row in vacating_finished:
			self.aisle[row] = 0
			self.row_vacating.pop(row)

		# Process passengers.
		# This basically iterates over all the passengers, and performs appropriate actions based on their state.
		seated_count = 0   # Number of passengers already seated.
		for i, p in enumerate(self.passengers):
			if i == 0: continue

			# To speed simulations we keep track of the `next_action_t` - a time when a given passenger may do the next action.
			# E.g. if walking takes 10 units of time, and a given passenger just started to walk, then we don't need to do anything
			# for him for the next 9 units of time.
			if p.next_action_t > self.t: continue

			match p.state:
				case State.BOARDING_QUEUE:
					# If the first space in the aisle is empty, move there.
					if self.aisle[0] == 0:
						self.aisle[0] = i
						p.state = State.MOVE_WAIT
						p.x = 0
						p.y = 0
						p.next_action_t = self.t + 1
						self.history[i].append([self.t, 0, 0, int(State.BOARDING_QUEUE)])
					
					# All the following passengers must also be in the queue.
					break

				case State.MOVE_WAIT:
					# Check if the next row is empty.
					if self.aisle[p.y+1] != 0 or p.y+1 in self.row_vacating:
						continue
					
					# We can go!
					p.next_action_t = self.t + SPEED_MOVE
					p.state = State.MOVE_TO_ROW
					self.history[i].append([self.t, 0, p.y, int(p.state)])

					self.aisle[p.y] = 0
					p.y += 1
					self.aisle[p.y] = i


				case State.MOVE_TO_ROW:
					# We just moved to the next row.
					if p.y == p.seat_row:
						# Did we reach the seat?
						if p.has_baggage:
							p.state = State.STOW_BAGGAGE
							p.next_action_t = self.t + SPEED_STOW_BAGGAGE
							self.history[i].append([self.t, 0, p.y, int(p.state)])
						else:
							if self.is_seat_accessible(row=p.seat_row, seat=p.seat):
								p.state = State.SEATING
								p.next_action_t = self.t + SPEED_SEATING
							else:
								waiting_time = self.vacate_row(i, p.seat_row, p.seat)
								p.state = State.WAIT_TO_SEAT
								p.next_action_t = self.t + waiting_time
							self.history[i].append([self.t, 0, p.y, int(p.state)])
					else:
						# We still need to reach our row.
						if self.aisle[p.y+1] != 0 or p.y+1 in self.row_vacating:
							p.state = State.MOVE_WAIT
							self.history[i].append([self.t, 0, p.y, int(p.state)])
							continue

						p.next_action_t = self.t + SPEED_MOVE
						self.history[i].append([self.t, 0, p.y, int(p.state)])

						self.aisle[p.y] = 0
						p.y += 1
						self.aisle[p.y] = i

				case State.STOW_BAGGAGE:
					ind = 0 if p.seat < 0 else 1
					self.baggage_bin[p.seat_row][ind] += 1
					self.history_baggage.append([self.t, p.seat_row, ind])

					if self.is_seat_accessible(row=p.seat_row, seat=p.seat):
						p.state = State.SEATING
						p.next_action_t = self.t + SPEED_SEATING
					else:
						waiting_time = self.vacate_row(i, p.seat_row, p.seat)
						p.state = State.WAIT_TO_SEAT
						p.next_action_t = self.t + waiting_time
					self.history[i].append([self.t, 0, p.y, int(p.state)])


				case State.VACATING_ROW:
					p.x = 0
					self.history[i].append([self.t, p.x, p.y, int(State.VACATING_ROW)])
					
				case State.RESEATING:
					# This state is handled by self.row_vacating at the beginning of the function.
					pass

				case State.WAIT_TO_SEAT:
					# This state is handled by self.row_vacating at the beginning of the function.
					pass
					
				case State.SEATING:
					# If we moved from the aisle, mark it as empty.
					if p.x == 0 and p.y not in self.row_vacating:
						self.aisle[p.y] = 0

					# Move to the next seat.
					if p.seat > 0:
						p.x += 1
					else:
						p.x -= 1

					# Did we reach our seat?
					if p.x == p.seat:
						p.state = State.SEATED
						if p.seat > 0:
							self.side_right[p.y, p.seat-1] = i
						else:
							self.side_left[p.y, -p.seat-1] = i
					else:
						p.next_action_t = self.t + SPEED_SEATING

					self.history[i].append([self.t, p.x, p.y, int(p.state)])

				case State.SEATED:
					seated_count += 1

				case _:
					self.print_info(f'State {p.state} is not handled.')

		# Check whether everyone is already seated
		return seated_count == self.n_passengers
			
	# Save boarding history to a file.
	def serialize_history(self, path):
		with open(path, 'w') as f:
			# General parameters in the header.
			f.write(f'{self.n_rows} {self.dummy_rows} {self.n_seats_left} {self.n_seats_right} {self.n_passengers} {len(self.history_baggage)}\n')

			# Save passengers' history.
			for id, h in self.history.items():
				f.write(f'{len(h)}\n')
				for entry in h:
					f.write(' '.join(map(str, entry)) + '\n')

			# Save baggage history.
			for entry in self.history_baggage:
				f.write(' '.join(map(str, entry)) + '\n')
