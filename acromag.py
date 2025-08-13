#!/usr/bin/env python3
import os, struct, time, csv
from datetime import datetime
from pycomm3 import CIPDriver

# --- Configurable settings ---
IP = os.environ.get("XT1222_IP", "10.10.10.100")
COUNTS = float(os.environ.get("XT1222_COUNTS", "20000"))  # 20000 if Legacy Support = Yes
FULL_SCALE_VOLTS = 10.0
HZ = float(os.environ.get("XT1222_POLL_HZ", "2"))  # prints per second
CSV_PATH = os.environ.get("XT1222_CSV")  # e.g. XT1222_CSV=acromag_log.csv

# EtherNet/IP object params
CLASS_ASSEMBLY = 0x04
INSTANCE_INPUT = 0x65
ATTR_DATA = 0x03

def counts_to_volts(n):
    return (n / COUNTS) * FULL_SCALE_VOLTS

def main():
    period = 1.0 / HZ if HZ > 0 else 0.5

    # Prepare CSV if requested
    csv_file = None
    csv_writer = None
    if CSV_PATH:
        csv_file = open(CSV_PATH, "a", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["timestamp"] + [f"ch{i}_V" for i in range(8)])

    with CIPDriver(IP) as conn:
        while True:
            resp = conn.generic_message(
                service=0x0E,
                class_code=CLASS_ASSEMBLY,
                instance=INSTANCE_INPUT,
                attribute=ATTR_DATA,
                route_path=True
            )
            raw = resp.value
            if not isinstance(raw, (bytes, bytearray)):
                if isinstance(raw, list):
                    raw = struct.pack("<" + "B"*len(raw), *raw)
                else:
                    raw = bytes(raw)

            words = list(struct.unpack("<" + "H"*(len(raw)//2), raw))
            ch_counts = [struct.unpack("<h", struct.pack("<H", w))[0] for w in words[:8]]
            ch_volts = [counts_to_volts(n) for n in ch_counts]

            # Print to terminal
            for i, v in enumerate(ch_volts):
                print(f"ch{i}: {v:+.3f}V")
            print()

            # Write to CSV
            if csv_writer:
                csv_writer.writerow([datetime.now().isoformat(timespec="milliseconds")] +
                                    [f"{v:.6f}" for v in ch_volts])
                csv_file.flush()

            time.sleep(period)

    if csv_file:
        csv_file.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
