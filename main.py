import numpy as np
import plane_boarding
import os


OUTPUT_DIR = '~/plane_boarding'


def save_history(simulation, n=1):
	for passengers_proportion in [1.0]:
		for boarding_zone in plane_boarding.BoardingZones:
			simulation.set_boarding_zones(boarding_zone)
			print(boarding_zone.name.lower())
			for i in range(n):
				simulation.run()
				file_name = f'{boarding_zone.name.lower()}_{passengers_proportion}_{simulation.n_rows}_{simulation.n_seats_left}_history_{i}.txt'
				simulation.serialize_history(os.path.join(OUTPUT_DIR, file_name))
			break

def measure_boarding_time(simulation, n=10):
	for passengers_proportion in [0.8, 1.0]:
		print('')
		for boarding_zone in plane_boarding.BoardingZones:
			simulation.set_passengers_proportion(passengers_proportion)
			simulation.set_boarding_zones(boarding_zone)
			simulation.run_multiple(n)

			print(boarding_zone, passengers_proportion, np.mean(simulation.boarding_time))
			
			file_name = f'{boarding_zone.name.lower()}_{passengers_proportion}'
			full_path = os.path.join(OUTPUT_DIR, f'{file_name}_{simulation.n_rows}_{simulation.n_seats_left}_total_time.txt')

			with open(full_path, "w") as file:
				file.write(f'{boarding_zone.name.lower()} {passengers_proportion}\n')
				file.write(' '.join(map(str, simulation.boarding_time)))


def save_boarding_orders(simulation):
	for boarding_zone in plane_boarding.BoardingZones:
		simulation.set_boarding_zones(boarding_zone)
		simulation.reset()

		print(boarding_zone)
		simulation.print_boarding_order()

		full_path = os.path.join(OUTPUT_DIR, f'{boarding_zone.name.lower()}_{simulation.n_rows}_{simulation.n_seats_left}_boarding_order.txt')

		with open(full_path, "w") as file:
			for i in range(simulation.dummy_rows, simulation.n_rows+simulation.dummy_rows):
				row = list(simulation.boarding_order_left[i, :][::-1]) + [-1] + list(simulation.boarding_order_right[i, :])
				file.write(' '.join(map(str, row)) + '\n')


def main():
	if not os.path.exists(OUTPUT_DIR):
		os.makedirs(OUTPUT_DIR)

	simulation = plane_boarding.Simulation(quiet_mode=True, dummy_rows=2)
	simulation.set_custom_aircraft(n_rows=16, n_seats_left=3, n_seats_right=3)
	simulation.set_passengers_proportion(1.0)
	simulation.set_boarding_zones(plane_boarding.BoardingZones.RANDOM)

	save_boarding_orders(simulation)
	save_history(simulation, n=1)
	measure_boarding_time(simulation, n=5)

if __name__ == "__main__":
	main()