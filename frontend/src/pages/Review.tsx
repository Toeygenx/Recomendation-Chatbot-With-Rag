import { useState } from "react";
import { Send, CheckCircle } from "lucide-react";
import Layout from "@/components/Layout";
import { submitReview } from "@/services/chatApi";
import CourseSearchInput from "@/components/CourseSearchInput";
import { Course } from "@/tpye/courses";
import { toast } from "@/hooks/use-toast";
import { useCourses } from "@/hooks/useCourses";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const MIN_LENGTH = 30;
const MAX_LENGTH = 500;

const Review = () => {
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [reviewText, setReviewText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  
  const { data: courses = [], isLoading: isLoadingCourses } = useCourses();

  const getValidationState = () => {
    const length = reviewText.length;
    if (length === 0) return { status: "empty", message: "" };
    if (length < MIN_LENGTH) {
      return {
        status: "error",
        message: `กรุณาเขียนอย่างน้อย ${MIN_LENGTH} ตัวอักษร (เหลืออีก ${MIN_LENGTH - length} ตัว)`,
      };
    }
    if (length >= MAX_LENGTH) {
      return { status: "max", message: "ถึงขีดจำกัดแล้ว" };
    }
    if (length >= MAX_LENGTH - 100) {
      return { status: "warning", message: `เหลืออีก ${MAX_LENGTH - length} ตัวอักษร` };
    }
    return { status: "valid", message: "" };
  };

  const validation = getValidationState();
  const isValidLength = reviewText.length >= MIN_LENGTH && reviewText.length <= MAX_LENGTH;

  const handleSubmit = async () => {
    if (!selectedCourse) {
      toast({
        title: "กรุณาเลือกรายวิชา",
        description: "เลือกรายวิชาที่ต้องการรีวิว",
        variant: "destructive",
      });
      return;
    }

    if (!isValidLength) {
      toast({
        title: "ความยาวรีวิวไม่ถูกต้อง",
        description: `กรุณาเขียนรีวิว ${MIN_LENGTH}-${MAX_LENGTH} ตัวอักษร`,
        variant: "destructive",
      });
      return;
    }


    setIsSubmitting(true);

    try {
      await submitReview({
        course_id: selectedCourse.course_id,
        review_content: reviewText.trim(),
        course_name: selectedCourse.course_name_th,
        credits: String(selectedCourse.credits),
        faculty: selectedCourse.faculty,
        category_64: selectedCourse.category_64,
        competency_67: selectedCourse.competency_67,
      });

      toast({
        title: "ส่งรีวิวสำเร็จ",
        description: "ขอบคุณที่ร่วมแบ่งปันประสบการณ์ครับ",
      });

      setIsSubmitting(false);
      setIsSuccess(true);
      
      setTimeout(() => {
        setSelectedCourse(null);
        setReviewText("");
        setIsSuccess(false);
      }, 2000);
    } catch (error) {
      console.error(error);
      setIsSubmitting(false);
      toast({
        title: "เกิดข้อผิดพลาด",
        description: "ไม่สามารถส่งรีวิวได้ กรุณาลองใหม่ภายหลัง",
        variant: "destructive",
      });
    }
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="text-center mb-8 animate-fade-in">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            เขียนรีวิว<span className="text-primary"> รายวิชา</span>
          </h1>
          <p className="text-muted-foreground">
            แชร์ประสบการณ์เพื่อช่วยน้องๆ ในการเลือกวิชา
          </p>
        </div>

        <div className="space-y-6 animate-slide-up">
          {/* Course search */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              เลือกรายวิชา
            </label>
            <CourseSearchInput
              selectedCourse={selectedCourse}
              onSelect={setSelectedCourse}
              onClear={() => setSelectedCourse(null)}
              courses={courses}
            />
          </div>

          {/* Review textarea */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              เขียนรีวิว
            </label>
            <textarea
              value={reviewText}
              onChange={(e) => setReviewText(e.target.value)}
              maxLength={MAX_LENGTH}
              placeholder="แชร์ประสบการณ์การเรียนวิชานี้ เช่น เนื้อหา อาจารย์ผู้สอน งานที่ต้องทำ การสอบ..."
              rows={6}
              className={`w-full bg-secondary/50 border rounded-xl p-4 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all resize-none ${
                validation.status === "error" ? "border-destructive" : "border-border"
              }`}
            />
            <div className="flex justify-between items-center mt-1">
              {validation.message ? (
                <p
                  className={`text-xs ${
                    validation.status === "error" || validation.status === "max"
                      ? "text-destructive"
                      : validation.status === "warning"
                      ? "text-yellow-500"
                      : "text-muted-foreground"
                  }`}
                >
                  {validation.message}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  ขั้นต่ำ {MIN_LENGTH} ตัวอักษร
                </p>
              )}
              <p
                className={`text-xs ${
                  validation.status === "error"
                    ? "text-destructive"
                    : validation.status === "warning" || validation.status === "max"
                    ? "text-yellow-500"
                    : reviewText.length >= MIN_LENGTH
                    ? "text-green-500"
                    : "text-muted-foreground"
                }`}
              >
                {reviewText.length}/{MAX_LENGTH}
              </p>
            </div>
          </div>


          {/* Submit button with Alert Dialog */}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <button
                disabled={isSubmitting || !selectedCourse || !isValidLength}
                className={`w-full py-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-all ${
                  isSuccess
                    ? "bg-success text-foreground"
                    : "bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                {isSubmitting ? (
                  <div className="loading-dots">
                    <span className="!bg-primary-foreground"></span>
                    <span className="!bg-primary-foreground"></span>
                    <span className="!bg-primary-foreground"></span>
                  </div>
                ) : isSuccess ? (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    ส่งรีวิวสำเร็จ!
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    ส่งรีวิว
                  </>
                )}
              </button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>ยืนยันการส่งรีวิว?</AlertDialogTitle>
                <AlertDialogDescription>
                  คุณต้องการส่งรีวิววิชานี้ใช่หรือไม่? รีวิวของคุณจะเป็นประโยชน์ต่อน้องๆ รุ่นต่อไป
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogAction onClick={handleSubmit}>ยืนยัน</AlertDialogAction>
                <AlertDialogCancel>ยกเลิก</AlertDialogCancel>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          <p className="text-center text-xs text-muted-foreground">
            รีวิวจะถูกนำไปใช้ในการสร้างคำตอบของ AI เท่านั้น
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default Review;
