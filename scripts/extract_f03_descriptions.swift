import Foundation
import PDFKit

// Extract the DESCRIÇÃO column for each validated numbered F03 row.
let pdf = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
let rows = try String(contentsOfFile: CommandLine.arguments[2], encoding: .utf8)
var result: [String: [String: Any]] = [:]
for line in rows.split(separator: "\n") {
    guard let data = line.data(using: .utf8),
          let row = try JSONSerialization.jsonObject(with: data) as? [String: Any],
          let source = row["source"] as? [String: Any],
          source["source_id"] as? String == "F03",
          let pageNumber = source["page"] as? Int,
          let bbox = row["bbox"] as? [Double], bbox.count == 4,
          let oid = row["occurrence_id"] as? String,
          let page = pdf.page(at: pageNumber - 1) else { continue }
    let height = page.bounds(for: .mediaBox).height
    let rectangle = CGRect(x: 123, y: height - bbox[3], width: 161, height: bbox[3] - bbox[1])
    let description = (page.selection(for: rectangle)?.string ?? "")
        .split(whereSeparator: \.isNewline).map { $0.trimmingCharacters(in: .whitespaces) }
        .filter { !$0.isEmpty }.joined(separator: " ")
    result[oid] = ["description": description, "page": pageNumber,
                   "source_row_number": row["source_row_number"] ?? NSNull(),
                   "pdf_sha256": source["sha256"] ?? "",
                   "column": "DESCRIÇÃO", "x0": 123, "x1": 284]
}
let output = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try output.write(to: URL(fileURLWithPath: CommandLine.arguments[3]))
