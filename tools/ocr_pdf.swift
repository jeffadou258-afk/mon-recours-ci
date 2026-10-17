// ocr_pdf.swift — Extraction de texte par OCR (macOS Vision + PDFKit)
//
// Outil de COLLECTE, isolé du runtime de l'agent : il est compilé une fois par
// `bin/ocr_collecter.py` et n'est jamais appelé par l'agent lui-même.
// Aucun accès réseau : il lit un PDF local et écrit un fichier texte local.
//
// Compilation :
//   swiftc -O tools/ocr_pdf.swift -o tools/ocr_pdf \
//          -framework Vision -framework PDFKit -framework AppKit
//
// Usage :
//   tools/ocr_pdf <entree.pdf> <sortie.txt> [echelle] [premiere_page] [derniere_page]
//
// Sortie : un fichier texte, une section par page, préfixée par « --- PAGE n --- ».
// Les lignes sont remises en ordre de lecture (haut→bas, gauche→droite) parce que
// Vision ne garantit pas l'ordre des observations.

import Foundation
import AppKit
import PDFKit
import Vision
import CoreGraphics

func erreur(_ message: String, _ code: Int32) -> Never {
    FileHandle.standardError.write(("ERREUR: " + message + "\n").data(using: .utf8)!)
    exit(code)
}

let arguments = CommandLine.arguments
guard arguments.count >= 3 else {
    erreur("usage: ocr_pdf <entree.pdf> <sortie.txt> [echelle] [page_debut] [page_fin]", 2)
}
let cheminEntree = arguments[1]
let cheminSortie = arguments[2]
let echelle = arguments.count > 3 ? (Double(arguments[3]) ?? 3.0) : 3.0
let pageDebut = arguments.count > 4 ? (Int(arguments[4]) ?? 1) : 1

guard let document = PDFDocument(url: URL(fileURLWithPath: cheminEntree)) else {
    erreur("PDF illisible : \(cheminEntree)", 3)
}
let total = document.pageCount
let pageFin = arguments.count > 5 ? min(Int(arguments[5]) ?? total, total) : total
guard pageDebut >= 1, pageFin >= pageDebut else {
    erreur("plage de pages invalide : \(pageDebut)..\(pageFin)", 4)
}

// Reconnaissance en français, niveau « accurate », correction linguistique active.
func requeteOCR() -> VNRecognizeTextRequest {
    let requete = VNRecognizeTextRequest()
    requete.recognitionLevel = .accurate
    requete.recognitionLanguages = ["fr-FR", "en-US"]
    requete.usesLanguageCorrection = true
    return requete
}

var sortie = ""
var pagesTraitees = 0
var pagesVides = 0
var totalLignes = 0

for index in (pageDebut - 1)..<pageFin {
    guard let page = document.page(at: index) else { continue }
    let cadre = page.bounds(for: .mediaBox)
    let largeur = Int(cadre.width * echelle)
    let hauteur = Int(cadre.height * echelle)
    guard largeur > 0, hauteur > 0 else { continue }

    guard let contexte = CGContext(
        data: nil,
        width: largeur,
        height: hauteur,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else { continue }

    // Fond blanc : un PDF scanné peut avoir un fond transparent.
    contexte.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    contexte.fill(CGRect(x: 0, y: 0, width: largeur, height: hauteur))
    contexte.scaleBy(x: CGFloat(echelle), y: CGFloat(echelle))
    contexte.translateBy(x: -cadre.origin.x, y: -cadre.origin.y)
    page.draw(with: .mediaBox, to: contexte)

    guard let image = contexte.makeImage() else { continue }

    let requete = requeteOCR()
    let gestionnaire = VNImageRequestHandler(cgImage: image, options: [:])
    do {
        try gestionnaire.perform([requete])
    } catch {
        FileHandle.standardError.write("page \(index + 1) : échec OCR (\(error))\n".data(using: .utf8)!)
        continue
    }

    let observations: [VNRecognizedTextObservation] = requete.results ?? []

    // Ordre de lecture : y décroissant (Vision : origine en bas), puis x croissant.
    // La géométrie est portée par l'observation, pas par le texte reconnu.
    // Les blocs dont le centre vertical est à moins de 1 % de hauteur sont
    // considérés sur la même ligne.
    let triees: [VNRecognizedTextObservation] = observations.sorted(
        by: { (gauche: VNRecognizedTextObservation, droite: VNRecognizedTextObservation) -> Bool in
            let dy = gauche.boundingBox.midY - droite.boundingBox.midY
            if abs(dy) > 0.010 { return dy > 0 }
            return gauche.boundingBox.minX < droite.boundingBox.minX
        })

    let lignes: [String] = triees.compactMap { $0.topCandidates(1).first?.string }
    totalLignes += lignes.count
    if lignes.isEmpty { pagesVides += 1 }

    sortie += "\n--- PAGE \(index + 1) ---\n"
    sortie += lignes.joined(separator: "\n")
    sortie += "\n"
    pagesTraitees += 1

    FileHandle.standardError.write("page \(index + 1)/\(pageFin) : \(lignes.count) lignes\n".data(using: .utf8)!)
}

do {
    try sortie.write(toFile: cheminSortie, atomically: true, encoding: .utf8)
} catch {
    erreur("écriture impossible : \(cheminSortie) (\(error))", 5)
}

// Résumé machine lisible sur la sortie standard : le script appelant le journalise.
let resume: [String: Any] = [
    "pages_pdf": total,
    "pages_traitees": pagesTraitees,
    "pages_sans_texte": pagesVides,
    "lignes_reconnues": totalLignes,
    "echelle": echelle,
    "fichier_sortie": cheminSortie,
]
if let donnees = try? JSONSerialization.data(withJSONObject: resume, options: [.sortedKeys]),
   let texte = String(data: donnees, encoding: .utf8) {
    print(texte)
}
