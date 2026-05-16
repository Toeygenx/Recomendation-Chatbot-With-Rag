import { useState, useRef, useEffect } from "react";
import { Search, X } from "lucide-react";
import { Course } from "@/tpye/courses";

interface CourseSearchInputProps {
  onSelect: (course: Course) => void;
  selectedCourse: Course | null;
  onClear: () => void;
  courses: Course[];
}

const CourseSearchInput = ({ onSelect, selectedCourse, onClear, courses }: CourseSearchInputProps) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Course[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length > 0) {
      const lowerQuery = query.toLowerCase();
      const searchResults = courses.filter(
        (course) =>
          course.course_id.toLowerCase().includes(lowerQuery) ||
          course.course_name_th.toLowerCase().includes(lowerQuery)
      );
      setResults(searchResults);
      setIsOpen(searchResults.length > 0);
    } else {
      setResults([]);
      setIsOpen(false);
    }
    setHighlightedIndex(-1);
  }, [query]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : prev));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (highlightedIndex >= 0) {
        handleSelect(results[highlightedIndex]);
      } else if (results.length > 0) {
        handleSelect(results[0]);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const handleSelect = (course: Course) => {
    onSelect(course);
    setQuery("");
    setIsOpen(false);
  };

  if (selectedCourse) {
    return (
      <div className="glass-card p-4 flex items-center justify-between animate-fade-in">
        <div>
          <span className="text-xs text-muted-foreground">รายวิชาที่เลือก</span>
          <p className="text-foreground font-medium">
            {selectedCourse.course_id} - {selectedCourse.course_name_th}
          </p>
        </div>
        <button
          onClick={onClear}
          className="p-2 hover:bg-secondary rounded-lg transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => query.trim() && results.length > 0 && setIsOpen(true)}
          placeholder="ค้นหารหัสวิชาหรือชื่อวิชา..."
          className="w-full bg-secondary/50 border border-border rounded-xl py-3 pl-12 pr-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
        />
      </div>

      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-2 glass-card overflow-hidden animate-fade-in"
        >
          <ul className="max-h-60 overflow-y-auto">
            {results.map((course, index) => (
              <li
                key={course.course_id}
                onClick={() => handleSelect(course)}
                className={`px-4 py-3 cursor-pointer transition-colors ${
                  index === highlightedIndex
                    ? "bg-primary/20"
                    : "hover:bg-secondary"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono bg-secondary px-2 py-1 rounded text-muted-foreground">
                    {course.course_id}
                  </span>
                  <span className="text-foreground">{course.course_name_th}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CourseSearchInput;
