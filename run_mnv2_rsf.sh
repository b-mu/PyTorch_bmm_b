for n in 1 10 50 100
do
	python benchmark_bmm_sim.py -i 3 32 32 32 32 16 96 96 16 24 144 144 24 144 144 32 192 192 32 192 192 32 192 192 64 384 384 64 384 384 64 384 384 64 384 384 64 96 576 576 96 576 576 96 576 576 160 960 960 160 960 960 160 960 960 160 320 -o 32 32 32 16 16 96 96 24 24 144 144 24 144 144 32 192 192 32 192 192 32 192 192 64 384 384 64 384 384 64 384 384 64 384 384 96 96 576 576 96 576 576 96 576 576 160 960 960 160 960 960 160 960 960 320 320 1280 -n $n --batch-size 128
done
