# Data and third-party notices

The project's MIT license applies to newly written application code, not a
relicensing of scientific data or bundled libraries.

## Scientific data

FlyWire Consortium / Princeton Neuroscience Institute and collaborators.
Dorkenwald, S. et al. Neuronal wiring diagram of an adult brain. Nature 634,
124–138 (2024). https://doi.org/10.1038/s41586-024-07558-y

Data portal and original terms: https://codex.flywire.ai/ and https://flywire.ai/.
The current pipeline downloads neurons.csv.gz, classification.csv.gz,
coordinates.csv.gz and connections.csv.gz directly from the official bucket:
https://storage.googleapis.com/flywire-data/codex/data/fafb/783/
This location is published by the official Codex project:
https://github.com/murthylab/codex/blob/main/codex/data/local_data_loader.py
No data from a third-party simulation project is loaded by the current pipeline.

FlyWire states that published data is available under CC BY-NC 4.0:
https://edit.flywire.ai/principles.html
License: https://creativecommons.org/licenses/by-nc/4.0/
Retain attribution, this license reference and a description of modifications;
the noncommercial restriction applies to scientific data, including the data
bundled with desktop builds. MIT applies to application code only.

Modifications: aggregate positive synapse counts by directed neuron pair across
neuropils; average annotation coordinates and transform display axes; derive UI
categories and separate educational signed weights. No biological validation.
Checksums, download URLs and object generations are in data/manifest.json.

## Historical attribution (not a current data dependency)

Earlier local prototypes used a snedea/flybrain data snapshot at commit
9191824d17871b7851645782d53d23f213ddb938. That data path has been replaced.
The earlier upstream notice is retained for attribution; it does not license
FlyWire scientific data or imply that current downloads pass through that project.

https://github.com/snedea/flybrain . Original license notice retained below:

MIT License

Copyright (c) [2017] [Seth Miller]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Runtime

PySide6 / Qt: LGPL v3 / GPL / commercial alternatives, https://www.qt.io/qt-for-python .
Dynamic Qt libraries remain separate in the portable application's _internal directory.
Pyqtgraph: MIT. PyOpenGL: BSD. NumPy / SciPy: BSD. OpenCV: Apache-2.0
and component licenses. Python: PSF license. Their applicable distribution
license files are bundled in _internal/third-party-licenses.

PyAV (BSD) and its bundled FFmpeg libraries provide timestamped local audio
decoding. Qt Multimedia supplies optional human monitoring. Their distribution
notices are included in the corresponding dependency license directories.
