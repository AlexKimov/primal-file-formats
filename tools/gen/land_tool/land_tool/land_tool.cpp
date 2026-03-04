// land_tool.cpp: определяет точку входа для консольного приложения.
//

#include "stdafx.h"

#include <iostream>
#include <fstream>
#include <vector>
#include <cmath>
#include <cstdint>
#include <algorithm>
#include <string>
#include <iomanip>
#include <sys/stat.h>

// Default Configuration Constants
const float DEFAULT_MINIMUM_GLOBAL_RESOLUTION = 256.0f;

struct ROAMConfig {
	int size = 0;
	std::string inputFile = "";
	std::string outputFile = "";
	bool autoSize = true;

	float neighbor_smooth_k = -1.0f;
	float error_sensitivity = 1.0f;
	float noise_threshold = 0.0f;
	float norm_reference_max = 0.0f;
	bool verbose = false;
};

// Get file size in bytes
std::streamoff GetFileSize(const std::string& filename) {
	std::ifstream file(filename, std::ios::binary | std::ios::ate);
	if (!file) return -1;
	return file.tellg();
}

// Calculate size from file size (assuming 16-bit signed int, square grid)
int CalculateSizeFromFile(const std::string& filename, bool verbose) {
	std::streamoff fileSize = GetFileSize(filename);

	if (fileSize <= 0) {
		std::cerr << "Error: Cannot determine file size." << std::endl;
		return -1;
	}

	// Each pixel is 2 bytes (int16_t)
	if (fileSize % 2 != 0) {
		std::cerr << "Error: File size is not divisible by 2 (expected 16-bit data)." << std::endl;
		return -1;
	}

	int totalPixels = fileSize / 2;
	int size = static_cast<int>(std::sqrt(totalPixels));

	// Verify it's a perfect square
	if (size * size != totalPixels) {
		std::cerr << "Error: File size does not match a square grid." << std::endl;
		std::cerr << "       Total pixels: " << totalPixels << ", sqrt: " << size << std::endl;
		return -1;
	}

	if (verbose) {
		std::cout << "File size: " << fileSize << " bytes" << std::endl;
		std::cout << "Total pixels: " << totalPixels << std::endl;
		std::cout << "Calculated dimensions: " << size << " x " << size << std::endl;
	}

	// Warn if not a typical ROAM size (2^n + 1)
	if (verbose) {
		bool isRoamSize = false;
		for (int n = 1; n <= 12; ++n) {
			if (size == (1 << n) + 1) {
				isRoamSize = true;
				break;
			}
		}
		if (!isRoamSize) {
			std::cout << "Warning: Size " << size << " is not a typical ROAM dimension (2^n + 1)." << std::endl;
			std::cout << "         Typical sizes: 129, 257, 513, 1025, 2049" << std::endl;
		}
		else {
			std::cout << "Dimensions match standard ROAM grid format." << std::endl;
		}
	}

	return size;
}

class ROAMRoughness {
private:
	ROAMConfig config;
	int size;
	std::vector<int16_t> heightmap;
	std::vector<float> roughness;
	float calculated_k;
	float global_max_error = 0.0f;

	inline float HT(int x, int z) const {
		if (x < 0 || x >= size || z < 0 || z >= size) return 0.0f;
		return static_cast<float>(heightmap[z * size + x]);
	}

	inline float& ROUGHNESS(int x, int z) {
		return roughness[z * size + x];
	}

	inline float ROUGHNESS(int x, int z) const {
		return roughness[z * size + x];
	}

	float CalculateAutoK() const {
		return DEFAULT_MINIMUM_GLOBAL_RESOLUTION / (2.0f * (DEFAULT_MINIMUM_GLOBAL_RESOLUTION - 2.0f));
	}

	void AddHError(int xmin, int zmin, int xmax, int zmax, float* pmax_error) {
		float h1 = HT(xmin, zmin);
		float h2 = HT(xmax, zmax);

		int x_mid = (xmin + xmax) / 2;
		int z_mid = (zmin + zmax) / 2;

		float h_mid = HT(x_mid, z_mid);
		float height_error = std::abs(h_mid - ((h1 + h2) * 0.5f));

		height_error *= config.error_sensitivity;

		if (height_error < config.noise_threshold) {
			height_error = 0.0f;
		}

		if (height_error > *pmax_error) {
			*pmax_error = height_error;
		}
	}

public:
	ROAMRoughness(const ROAMConfig& cfg) : config(cfg), size(cfg.size) {
		heightmap.resize(size * size, 0);
		roughness.resize(size * size, 0.0f);

		if (config.neighbor_smooth_k < 0.0f) {
			calculated_k = CalculateAutoK();
		}
		else {
			calculated_k = config.neighbor_smooth_k;
		}
	}

	bool LoadHeightmap() {
		std::ifstream file(config.inputFile, std::ios::binary);
		if (!file) {
			std::cerr << "Error: Cannot open input file " << config.inputFile << std::endl;
			return false;
		}
		file.read(reinterpret_cast<char*>(heightmap.data()), sizeof(int16_t) * size * size);
		if (file.gcount() != sizeof(int16_t) * size * size) {
			std::cerr << "Error: Input file size does not match dimensions." << std::endl;
			return false;
		}
		return true;
	}

	void Calculate() {
		int level = 1;
		int edge_length = 2;
		float max_error;
		float d2;

		if (config.verbose) {
			std::cout << "Using Neighbor Smooth K: " << calculated_k << std::endl;
			std::cout << "Error Sensitivity: " << config.error_sensitivity << std::endl;
			std::cout << "Noise Threshold: " << config.noise_threshold << std::endl;
			std::cout << "Starting calculation..." << std::endl;
		}

		while (edge_length <= size) {
			if (config.verbose && edge_length % 32 == 0) {
				std::cout << "Processing LOD level (edge_length=" << edge_length << ")" << std::endl;
			}

			for (int x = level; x < size; x += edge_length) {
				for (int z = level; z < size; z += edge_length) {
					max_error = 0.0f;

					AddHError(x - level, z - level, x - level, z + level, &max_error);
					AddHError(x + level, z - level, x + level, z + level, &max_error);
					AddHError(x - level, z - level, x + level, z - level, &max_error);
					AddHError(x - level, z + level, x + level, z + level, &max_error);
					AddHError(x - level, z - level, x + level, z + level, &max_error);
					AddHError(x - level, z + level, x + level, z - level, &max_error);

					if (edge_length > 0)
						d2 = max_error / static_cast<float>(edge_length);
					else
						d2 = max_error;

					if (level > 1) {
						if (z - level >= 0) d2 = std::max(d2, calculated_k * ROUGHNESS(x, z - level));
						if (z + level < size) d2 = std::max(d2, calculated_k * ROUGHNESS(x, z + level));
						if (x - level >= 0) d2 = std::max(d2, calculated_k * ROUGHNESS(x - level, z));
						if (x + level < size) d2 = std::max(d2, calculated_k * ROUGHNESS(x + level, z));
					}

					ROUGHNESS(x, z) = d2;
					if (d2 > global_max_error) global_max_error = d2;

					auto update_corner = [&](int cx, int cz) {
						if (cx >= 0 && cx < size && cz >= 0 && cz < size) {
							float& val = ROUGHNESS(cx, cz);
							if (d2 > val) val = d2;
							if (d2 > global_max_error) global_max_error = d2;
						}
					};

					update_corner(x - level, z - level);
					update_corner(x - level, z + level);
					update_corner(x + level, z + level);
					update_corner(x + level, z - level);
				}
			}
			level *= 2;
			edge_length *= 2;
		}
	}

	bool SaveRoughnessMap() {
		std::vector<uint8_t> output_buffer(size * size);
		float scale_max = (config.norm_reference_max > 0.0f) ? config.norm_reference_max : global_max_error;

		if (scale_max < 0.0001f) scale_max = 0.0001f;

		if (config.verbose) {
			std::cout << "Global Max Error Found: " << global_max_error << std::endl;
			std::cout << "Normalization Scale Max: " << scale_max << std::endl;
		}

		for (int i = 0; i < size * size; ++i) {
			float normalized = roughness[i] / scale_max;
			int val = static_cast<int>(std::round(normalized * 255.0f));
			if (val < 0) val = 0;
			if (val > 255) val = 255;
			output_buffer[i] = static_cast<uint8_t>(val);
		}

		std::ofstream file(config.outputFile, std::ios::binary);
		if (!file) {
			std::cerr << "Error: Cannot create output file " << config.outputFile << std::endl;
			return false;
		}
		file.write(reinterpret_cast<char*>(output_buffer.data()), sizeof(uint8_t) * size * size);

		return true;
	}
};

void PrintUsage(const char* progName) {
	std::cout << "ROAM Roughness Map Generator (Auto-Size)\n";
	std::cout << "Usage: " << progName << " <input_raw> <output_raw> [size] [options]\n\n";
	std::cout << "Arguments:\n";
	std::cout << "  input_raw   : 16-bit signed integer heightmap (binary)\n";
	std::cout << "  output_raw  : 8-bit unsigned integer roughness map (binary)\n";
	std::cout << "  size        : Optional. Width/Height. Auto-calculated if omitted.\n\n";
	std::cout << "Options:\n";
	std::cout << "  -k <float>  : Neighbor smoothing factor. Default: Auto-calc (~0.5).\n";
	std::cout << "  -e <float>  : Error sensitivity scale. Default: 1.0.\n";
	std::cout << "  -n <float>  : Noise threshold. Default: 0.0.\n";
	std::cout << "  -r <float>  : Normalization reference max. Default: Auto.\n";
	std::cout << "  -v          : Verbose output (progress and stats).\n";
	std::cout << "  -h          : Show this help message.\n";
}

bool ParseArgs(int argc, char* argv[], ROAMConfig& config) {
	if (argc < 3) return false;

	config.inputFile = argv[1];
	config.outputFile = argv[2];

	// Check if third argument is a number (size) or a flag
	if (argc > 3) {
		std::string arg3 = argv[3];
		if (arg3[0] == '-') {
			// It's a flag, use auto-size
			config.autoSize = true;
		}
		else {
			// It's a size value
			config.size = std::atoi(arg3.c_str());
			if (config.size > 0) {
				config.autoSize = false;
			}
			else {
				std::cerr << "Error: Invalid size value." << std::endl;
				return false;
			}
		}
	}
	else {
		config.autoSize = true;
	}

	for (int i = config.autoSize ? 3 : 4; i < argc; ++i) {
		std::string arg = argv[i];
		if (arg == "-v") {
			config.verbose = true;
		}
		else if (arg == "-h") {
			return false; // Trigger help
		}
		else if (arg == "-k" && i + 1 < argc) {
			config.neighbor_smooth_k = std::atof(argv[++i]);
		}
		else if (arg == "-e" && i + 1 < argc) {
			config.error_sensitivity = std::atof(argv[++i]);
		}
		else if (arg == "-n" && i + 1 < argc) {
			config.noise_threshold = std::atof(argv[++i]);
		}
		else if (arg == "-r" && i + 1 < argc) {
			config.norm_reference_max = std::atof(argv[++i]);
		}
		else {
			std::cerr << "Unknown argument: " << arg << std::endl;
			return false;
		}
	}
	return true;
}

int main(int argc, char* argv[]) {
	ROAMConfig config;

	// Check for help flag first
	for (int i = 1; i < argc; ++i) {
		if (std::string(argv[i]) == "-h") {
			PrintUsage(argv[0]);
			return 0;
		}
	}

	if (!ParseArgs(argc, argv, config)) {
		PrintUsage(argv[0]);
		return 1;
	}

	std::cout << "Initializing ROAM Roughness Calculator..." << std::endl;

	// Auto-calculate size if not provided
	if (config.autoSize) {
		std::cout << "Auto-detecting dimensions from file..." << std::endl;
		config.size = CalculateSizeFromFile(config.inputFile, true);
		if (config.size <= 0) {
			return 1;
		}
	}
	else {
		std::cout << "Using manual dimensions: " << config.size << " x " << config.size << std::endl;
	}

	ROAMRoughness roam(config);

	std::cout << "Loading heightmap: " << config.inputFile << std::endl;
	if (!roam.LoadHeightmap()) {
		return 1;
	}

	std::cout << "Calculating roughness..." << std::endl;
	roam.Calculate();

	std::cout << "Saving roughness map: " << config.outputFile << std::endl;
	if (!roam.SaveRoughnessMap()) {
		return 1;
	}

	std::cout << "Done." << std::endl;
	return 0;
}