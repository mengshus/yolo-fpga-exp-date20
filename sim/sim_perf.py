from math import floor as floor
from math import ceil as ceil

# dump log file
import pickle
# argument passer
import argparse
import csv
import os

parser = argparse.ArgumentParser(description='Input parameters workload model.')
parser.add_argument('--workload', type=str, nargs='+', help='model.csv file')
parser.add_argument('--print', type=bool, nargs=1, default=False, help='print flag')
args = parser.parse_args()

model_file = open(args.workload[0], "r")
workload_config = csv.reader(model_file)

hw_ibuf_size = 100000
hw_obuf_size = 100000
hw_wbuf_size = 300000
hw_pe_d1 = 8
hw_pe_d2 = 8
hw_pe_d3 = 8
hw_rd_bandwidth = 20
hw_wr_bandwidth = 20

hw_th = hw_pe_d1 * hw_pe_d1 * hw_pe_d1

# final results for each layer (unit: cycle)
layer_perf = []


if __name__ == '__main__':

    for layer_item in workload_config:

        if layer_item[0] == "IDX":
            continue

        print("Processing layer:" + layer_item[0])
        [j, i, n, m, stride, h, w] = map(int, layer_item[2:9])

        # start a new layer, initial time to a very large number
        time = j*i*n*m*h*w

        for tm in range(1, m+1):
            for tn in range(1, n+1):
                for th in range(1, h+1, 5):
                    for tw in range(1, w+1,10):
                        # check1: memory size (Input)
                        if (i+tw*stride)*(j+th*stride)*tn > hw_ibuf_size:
                            continue
                        # check2: memory size (Output)
                        if tw*th*tm > hw_obuf_size:
                            continue
                        # check3: memory size (Weight)
                        if tn*tm*i*j > hw_wbuf_size:
                            continue

                        # computation time
                        # can only mapping m to pe_d3, thus, we should calculate the hw efficiency here
                        if tm < hw_pe_d3:
                            hw_eff = tm / hw_pe_d3
                        else:
                            hw_eff = 1
                        time_comp = ((i*j*tw*th*tm*tn)/(hw_th*hw_eff))*ceil(w/tw)*ceil(h/th)*ceil(m/tm)*ceil(n/tn)
                        # amount of in_act read
                        rd_inact = (i+tw*stride)*(j+th*stride)*tn*ceil(w/tw)*ceil(h/th)*ceil(m/tm)
                        # devide by 2 because rd bandwidth should be shared by in_act & w
                        time_rd_inact = rd_inact / (hw_rd_bandwidth / 2)
                        # amount of w read
                        rd_w = i*j*tn*tm*ceil(w/tw)*ceil(h/th)*ceil(m/tm)*ceil(n/tn)
                        time_rd_w = rd_w / (hw_rd_bandwidth / 2)
                        # amount of out_act write
                        wr_outact = tw*th*tm*ceil(n/tn)*ceil(m/tm)
                        time_wr_outact = wr_outact / hw_wr_bandwidth

                        time_max = max(time_comp, time_rd_inact, time_rd_w, time_wr_outact)

                        if time_max < time:
                            time = time_max
                            (opt_tm, opt_tn, opt_th, opt_tw) = (tm, tn, th, tw)
        # iterate over all options
        layer_perf.append([layer_item[0], int(time), opt_tm, opt_tn, opt_th, opt_tw, (j*i*n*m*h*w)/hw_pe_d1/hw_pe_d2/hw_pe_d3/time])

    print("All layer has been processed.")

    filename_res = "perf/"+args.workload[0][6:-4]+".csv"
    with open(filename_res, "w") as fh_res_csv:
        csvwriter = csv.writer(fh_res_csv,  delimiter=',')
        csvwriter.writerow(['IDX', 'CYCLE', 'OPT_TM', 'OPT_TN', 'OPT_TH', 'OPT_TW', 'HW_EFF'])
        for item in layer_perf:
            csvwriter.writerow([str(elem) for elem in item])
        print("The performance results have been written to" + filename_res)

