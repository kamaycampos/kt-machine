import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
let inURL = URL(fileURLWithPath: args[1]), outURL = URL(fileURLWithPath: args[2])
guard let ci = CIImage(contentsOf: inURL) else { fatalError("cannot read") }
let handler = VNImageRequestHandler(ciImage: ci, options: [:])
let req = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([req])
guard let obs = req.results?.first else { fatalError("no subject") }
// the largest instance only (the person in front), not people behind
var best = IndexSet(obs.allInstances)
if args.count > 3, let n = Int(args[3]) { best = IndexSet(integer: n) }
let buf = try obs.generateMaskedImage(ofInstances: best, from: handler, croppedToInstancesExtent: false)
let out = CIImage(cvPixelBuffer: buf)
let ctx = CIContext()
let cs = CGColorSpace(name: CGColorSpace.sRGB)!
try ctx.writePNGRepresentation(of: out, to: outURL, format: .RGBA8, colorSpace: cs)
print("instances:", obs.allInstances.count, "->", outURL.lastPathComponent)
