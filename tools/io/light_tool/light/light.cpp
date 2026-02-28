#include "stdafx.h"

#include <windows.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
#include <memory>
#include "ijl.h"

// Table sizes defined by IJL structure layouts
constexpr size_t QUANT_TABLE_SIZE = 164;
constexpr size_t HUFF_TABLE_SIZE = 1648;

// RAII wrapper for IJL Core Properties
class IjlSession {
public:
	JPEG_CORE_PROPERTIES props;

	IjlSession() {
		memset(&props, 0, sizeof(JPEG_CORE_PROPERTIES));
	}

	~IjlSession() {
		ijlFree(&props);
	}

	bool init() {
		return ijlInit(&props) == IJL_OK;
	}

	bool readHeader() {
		return ijlRead(&props, IJL_JBUFF_READHEADER) == IJL_OK;
	}

	bool readParams() {
		return ijlRead(&props, IJL_JBUFF_READPARAMS) == IJL_OK;
	}

	bool readImage() {
		return ijlRead(&props, IJL_JBUFF_READWHOLEIMAGE) == IJL_OK;
	}

	bool writeImage() {
		return ijlWrite(&props, IJL_JFILE_WRITEWHOLEIMAGE) == IJL_OK;
	}
};

// Manages JPEG Encoding Tables safely
class JpegTableStore {
private:
	std::vector<uint8_t> quantTables;
	std::vector<uint8_t> acHuffmanTables;
	std::vector<uint8_t> dcHuffmanTables;

public:
	DWORD nqtables = 0;
	DWORD maxquantindex = 0;
	DWORD nhuffActables = 0;
	DWORD nhuffDctables = 0;
	DWORD maxhuffindex = 0;

	void Initialize(JPEG_PROPERTIES* props) {
		nqtables = props->nqtables;
		maxquantindex = props->maxquantindex;
		nhuffActables = props->nhuffActables;
		nhuffDctables = props->nhuffDctables;
		maxhuffindex = props->maxhuffindex;

		if (nqtables > 0) {
			quantTables.resize(nqtables * QUANT_TABLE_SIZE);
			memcpy(quantTables.data(), &props->jFmtQuant[0], quantTables.size());
		}

		if (nhuffActables > 0) {
			acHuffmanTables.resize(nhuffActables * HUFF_TABLE_SIZE);
			memcpy(acHuffmanTables.data(), &props->jFmtAcHuffman[0], acHuffmanTables.size());
		}

		if (nhuffDctables > 0) {
			dcHuffmanTables.resize(nhuffDctables * HUFF_TABLE_SIZE);
			memcpy(dcHuffmanTables.data(), &props->jFmtDcHuffman[0], dcHuffmanTables.size());
		}
	}

	void ExportProperties(JPEG_PROPERTIES* props) {
		props->nqtables = nqtables;
		props->maxquantindex = maxquantindex;
		props->nhuffActables = nhuffActables;
		props->nhuffDctables = nhuffDctables;
		props->maxhuffindex = maxhuffindex;

		if (nqtables > 0) {
			memcpy(&props->jFmtQuant[0], quantTables.data(), quantTables.size());
		}
		if (nhuffActables > 0) {
			memcpy(&props->jFmtAcHuffman[0], acHuffmanTables.data(), acHuffmanTables.size());
		}
		if (nhuffDctables > 0) {
			memcpy(&props->jFmtDcHuffman[0], dcHuffmanTables.data(), dcHuffmanTables.size());
		}
	}
};

// Generates standard encoding tables using IJL
bool getStandardIJLEncodingTables(IJL_JPGSUBSAMPLING subsampling, DWORD quality, JPEG_PROPERTIES* outputProps) {
	IjlSession session;
	if (!session.init()) return false;

	std::vector<uint8_t> dibBuffer(16 * 16 * 3);
	std::vector<uint8_t> jpgBuffer(1768);

	// Setup for JPEG Write (Generate Tables)
	session.props.DIBBytes = dibBuffer.data();
	session.props.DIBWidth = 16;
	session.props.DIBHeight = 16;
	session.props.DIBPadBytes = 0;
	session.props.DIBChannels = 3;
	session.props.DIBSubsampling = IJL_NONE;
	session.props.JPGFile = NULL;
	session.props.JPGBytes = jpgBuffer.data();
	session.props.JPGSizeBytes = 1768;
	session.props.JPGWidth = 16;
	session.props.JPGHeight = 16;
	session.props.JPGChannels = 3;
	session.props.JPGColor = IJL_YCBCR;
	session.props.JPGSubsampling = subsampling;
	session.props.jquality = quality;

	if (ijlWrite(&session.props, IJL_JBUFF_WRITEWHOLEIMAGE) != IJL_OK) return false;

	// Re-initialize for JPEG Read to extract tables
	if (!session.init()) return false;

	session.props.JPGBytes = jpgBuffer.data();
	session.props.JPGSizeBytes = 1768;
	session.props.JPGColor = IJL_YCBCR;
	session.props.JPGSubsampling = subsampling;
	session.props.jquality = quality;

	if (!session.readHeader()) return false;

	JpegTableStore ctx;
	ctx.Initialize(&session.props.jprops);
	ctx.ExportProperties(outputProps);

	return true;
}

// Extracts and saves a single JPEG from the archive buffer
int write_jpeg_from_buffer(FILE* fp, const std::string& folder, const std::string& filename, int start_pos, int jpeg_size, int jsubsampling, int jquality) {
	IjlSession session;

	std::vector<uint8_t> jpeg_buffer(jpeg_size);

	long pos = ftell(fp);
	fseek(fp, start_pos, SEEK_SET);
	if (fread(jpeg_buffer.data(), 1, jpeg_size, fp) != jpeg_size) {
		fseek(fp, pos, SEEK_SET);
		return -1;
	}
	fseek(fp, pos, SEEK_SET);

	if (!session.init()) return -1;

	session.props.DIBBytes = NULL;
	session.props.JPGFile = NULL;
	session.props.JPGBytes = jpeg_buffer.data();
	session.props.JPGSizeBytes = jpeg_size;

	if (!session.readParams()) return -1;

	int width = session.props.JPGWidth;
	int height = session.props.JPGHeight;
	int channels = session.props.JPGChannels;

	// Force standard encoding tables (Quality 90)
	IJL_JPGSUBSAMPLING sampling = static_cast<IJL_JPGSUBSAMPLING>(jsubsampling);

	if (!getStandardIJLEncodingTables(sampling, jquality, &session.props.jprops)) return -1;

	int imageSize = width * height * channels;
	std::vector<uint8_t> dibBuffer(imageSize);
	session.props.DIBBytes = dibBuffer.data();
	session.props.DIBWidth = width;
	session.props.DIBHeight = height;
	session.props.DIBChannels = channels;
	session.props.DIBColor = IJL_BGR;
	session.props.DIBPadBytes = 0;

	if (!session.readImage()) return -1;

	// Re-init for write operation
	if (!session.init()) return -1;

	std::string fullPath = folder + filename;
	session.props.JPGFile = (char*)fullPath.c_str();
	session.props.JPGWidth = width;
	session.props.JPGHeight = height;
	session.props.JPGChannels = channels;
	session.props.JPGBytes = jpeg_buffer.data();
	session.props.JPGSizeBytes = jpeg_size;
	session.props.JPGColor = IJL_YCBCR;
	session.props.JPGSubsampling = sampling;
	session.props.jquality = jquality;

	session.props.DIBWidth = width;
	session.props.DIBHeight = height;
	session.props.DIBChannels = channels;
	session.props.DIBBytes = dibBuffer.data();
	session.props.DIBColor = IJL_BGR;
	session.props.DIBPadBytes = 0;

	if (!session.writeImage()) return -1;

	return 0;
}

// Ensures the specified directory path exists, creating it if necessary
void EnsureDirectoryExists(const std::string& path) {
	if (path.empty()) return;
	if (CreateDirectoryA(path.c_str(), NULL) || GetLastError() == ERROR_ALREADY_EXISTS) {
		return;
	}
	size_t pos = 0;
	while ((pos = path.find_first_of("\\/", pos + 1)) != std::string::npos) {
		std::string current = path.substr(0, pos);
		if (current.empty() || current.back() == ':') continue;
		CreateDirectoryA(current.c_str(), NULL);
	}
	CreateDirectoryA(path.c_str(), NULL);
}

// Handles .light archive parsing and extraction
class LightArchive {
private:
	FILE* fp;
	std::string outputPath;

	std::string ensureTrailingSlash(const std::string& path) {
		if (path.empty() || path.back() != '\\' && path.back() != '/') {
			return path + "/";
		}
		return path;
	}

public:
	LightArchive(const std::string& path, const std::string& output) : fp(nullptr) {
		EnsureDirectoryExists(output);
		fopen_s(&fp, path.c_str(), "rb");
		outputPath = ensureTrailingSlash(output);
	}

	~LightArchive() {
		if (fp) fclose(fp);
	}

	bool isOpen() const { return fp != nullptr; }

	int extract(const std::string& baseName) {
		int num1, num2, num3;
		fseek(fp, 15, SEEK_SET);
		fread(&num3, 4, 1, fp);
		fread(&num1, 4, 1, fp);
		fseek(fp, 27, SEEK_SET);
		fread(&num2, 4, 1, fp);
		fseek(fp, 16 * num2, SEEK_CUR);

		int subsmpl1, subsmpl2, subsmpl3, jquality1, jquality2, jquality3;
		fread(&subsmpl1, 4, 1, fp);
		fread(&jquality1, 4, 1, fp);
		fread(&subsmpl2, 4, 1, fp);
		fread(&jquality2, 4, 1, fp);
		fread(&subsmpl3, 4, 1, fp);
		fread(&jquality3, 4, 1, fp);

		int size1, size2;
		fread(&size1, 4, 1, fp);
		fread(&size2, 4, 1, fp);

		int size5 = num1 * num1 * num2;
		int size6 = num2 * (num1 * (num3 - 2) / size1 + 1) * (num1 * (num3 - 2) / size2 + 1);

		long start_pos = ftell(fp) + size5 * 4 + 4 + size6 * 4;
		char filename[256];
		int size;

		// Extract main textures
		for (int i = 0; i < size5; ++i) {
			fread(&size, 4, 1, fp);
			snprintf(filename, sizeof(filename), "%s_main_tetxures_%d.jpg", baseName.c_str(), i);
			if (write_jpeg_from_buffer(fp, outputPath, filename, start_pos, size, subsmpl1, jquality1) != 0) {
				fprintf(stderr, "Failed to read JPEG\n");
				return 1;
			}
			start_pos += size;
		}

		// Extract map
		fread(&size, 4, 1, fp);
		snprintf(filename, sizeof(filename), "%s_map.jpg", baseName.c_str());
		if (write_jpeg_from_buffer(fp, outputPath, filename, start_pos, size, subsmpl2, jquality2) != 0) {
			fprintf(stderr, "Failed to read JPEG\n");
			return 1;
		}
		start_pos += size;

		// Extract second textures
		for (int i = 0; i < size6; ++i) {
			fread(&size, 4, 1, fp);
			snprintf(filename, sizeof(filename), "%s_second_tetxures_%d.jpg", baseName.c_str(), i);
			if (write_jpeg_from_buffer(fp, outputPath, filename, start_pos, size, subsmpl3, jquality3) != 0) {
				fprintf(stderr, "Failed to read JPEG\n");
				return 1;
			}
			start_pos += size;
		}

		return 0;
	}
};

int main(int argc, char* argv[]) {
	if (argc < 2) {
		fprintf(stderr, "Usage: %s <file.light> [output_folder]\n", argv[0]);
		return 1;
	}

	const char* light_file = argv[1];
	const char* output_folder = (argc > 2) ? argv[2] : ".";

	// Extract base name from path for filenames
	std::string fullPath = light_file;
	size_t lastSlash = fullPath.find_last_of("\\/");
	std::string baseName = (lastSlash != std::string::npos) ? fullPath.substr(lastSlash + 1) : fullPath;
	// Remove extension for base name
	size_t lastDot = baseName.find_last_of(".");
	if (lastDot != std::string::npos) {
		baseName = baseName.substr(0, lastDot);
	}

	LightArchive archive(light_file, output_folder);
	if (!archive.isOpen()) {
		fprintf(stderr, "Cannot open file\n");
		return 1;
	}

	return archive.extract(baseName);
}