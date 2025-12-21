# &lt; DATA / AI SHELL >
## ... [<span style="color:#ff00ff">-</span>] DASH

- In researching / early development stage

## What
- DASH is a PTY (pseudoterminal) shell wrapper. 
- Core will be written in C++, that will support Python scripts as extensions to the core. 

## Scope
- Projects scope is to create a helpful extension for Data / AI Engineers or like minded people in their day-to-day tasks, running in their favorite shell.
- This project will use present technologies and as an open-source, allows others to contribute their ideas and features to it as well.
- Allows Python scripts so other Data / AI oriented people can create plugins in the language they are most confident in.

## Why
Why not, terminals should be smarter

## Build
### 1. Install dependencies
#### Ubuntu 24.04 LTS
- `sudo apt update`
- `sudo apt install build-essential cmake python3-dev g++-14`
#### macOS
- `xcode-select --install`
- `brew install cmake python`

### 2. Clone the repo and cd in to it
- `git clone https://github.com/mitro54/DASH.git`
- `cd DASH`

### 3. Create a build folder and cd in to it
- `mkdir build`
- `cd build`

### 4. Run cmake and make
- `cmake ..` or `cmake -DCMAKE_CXX_COMPILER=g++-14 ..` to make sure it uses GCC 14 for C++23 (Linux)
- `make`

### 5. Run it
`./DASH`