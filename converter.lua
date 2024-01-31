#!/usr/bin/env lua

if #arg < 2 then
	print("Usage:\n\tconverter.lua <values.lua path> <output file>")
	os.exit()
end

local file, error = io.open(arg[1], "r")
if file == nil then
	io.stderr:write("Failed to open input file: " .. error .. "\n")
	io.stderr:flush()
	os.exit(1)
end

file:close() -- we only needed this to check that we could read

dofile(arg[1])

local parts = {"{\n\t"}

for name, data in pairs(unitlist) do
	parts[#parts + 1] = string.format(
		[["%s": {
		"dir": %s,
		"ground": %d,
		"frames": %d,
		"unit": %s
	}]],
		name,
		data.directions or false,
		data.ground or 0,
		data.animframes or 1,
		data.unit or data.text or false
	)
	parts[#parts + 1] = ",\n\t"
end

parts[#parts + 1] = [["terrain_0": {
		"dir": false,
		"ground": 0,
		"frames": 1,
		"unit": false
	},
	"terrain_1": {
		"dir": false,
		"ground": 0,
		"frames": 1,
		"unit": false
	},
	"terrain_2": {
		"dir": false,
		"ground": 0,
		"frames": 1,
		"unit": false
	},
	"terrain_3": {
		"dir": false,
		"ground": 0,
		"frames": 1,
		"unit": false
	},
	"terrain_4": {
		"dir": false,
		"ground": 0,
		"frames": 1,
		"unit": false
	}
}]]

file, error = io.open(arg[2], "w")
if file == nil then
	io.stderr:write("Failed to open output file: " .. error .. "\n")
	io.stderr:flush()
	os.exit(1)
end

file:write(table.concat(parts))
file:close()
