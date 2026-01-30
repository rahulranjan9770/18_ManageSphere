from backend.generation.conflict_detector import ConflictDetector
from backend.models.query import EvidenceSource, Modality

def test_conflict():
    detector = ConflictDetector()
    
    source1 = EvidenceSource(
        source_id="1",
        source_file="text.txt",
        modality=Modality.TEXT,
        content="The operating voltage is 220V.",
        relevance_score=0.9,
        confidence=1.0
    )
    
    source2 = EvidenceSource(
        source_id="2",
        source_file="image.jpg",
        modality=Modality.IMAGE,
        content="Label: Voltage 110V",
        relevance_score=0.9,
        confidence=1.0
    )
    
    print("Testing with sources:")
    print(f"1. {source1.content}")
    print(f"2. {source2.content}")
    
    conflict = detector.detect_conflicts([source1, source2])
    
    if conflict:
        print("\nConflict DETECTED!")
        print(conflict.description)
        for p in conflict.perspectives:
            print(f"- {p['source']}: {p['claim']}")
    else:
        print("\nNo conflict detected.")

if __name__ == "__main__":
    test_conflict()
