
import { useQuery } from "@tanstack/react-query";
import { fetchCourses, CourseName } from "@/services/chatApi";
import { Course } from "@/tpye/courses";

export const useCourses = () => {
  return useQuery({
    queryKey: ["courses"],
    queryFn: fetchCourses,
    staleTime: Infinity, // Cache for the entire session
  });
};
