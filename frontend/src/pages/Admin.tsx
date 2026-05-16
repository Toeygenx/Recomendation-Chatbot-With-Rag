import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Edit3, Plus, Trash2, Save, X, Search, MessageSquare } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Course } from "@/tpye/courses";
import { useCourses } from "@/hooks/useCourses";
import { Review, fetchReviews, deleteReview, addCourse, updateCourse, deleteCourse } from "@/services/chatApi";
import CourseSearchInput from "@/components/CourseSearchInput";
import CourseForm from "@/components/CourseForm";
import { toast } from "@/hooks/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

type Mode = "edit" | "add";

const Admin = () => {
  const { isAuthenticated, isLoading, logout } = useAuth();
  const { data: courses = [], refetch } = useCourses();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("edit");
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [newCourse, setNewCourse] = useState<Course>({
    course_id: "",
    course_name_th: "",
    credits: 3,
    faculty: "",
    category_64: "",
    competency_67: "",
    doc_type: "",
    description: "",
    clos: "",
  });
  const [dialogType, setDialogType] = useState<"edit" | "delete" | "add" | "deleteReview" | null>(null);
  
  // Review Management State
  const [subMode, setSubMode] = useState<"info" | "reviews" | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewToDelete, setReviewToDelete] = useState<number | null>(null);
  const [viewReview, setViewReview] = useState<Review | null>(null); // For viewing full detail

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/admin/login");
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const handleSelectCourse = (course: Course) => {
    setSelectedCourse(course);
    setEditingCourse({ ...course });
    setSubMode(null); // Reset submode
  }; 
  
  const handleFetchReviews = async () => {
    if (selectedCourse) {
      try {
        const data = await fetchReviews(selectedCourse.course_id);
        setReviews(data);
      } catch (error) {
        console.error(error);
        toast({ title: "เกิดข้อผิดพลาด", description: "ไม่สามารถดึงข้อมูลรีวิวได้", variant: "destructive" });
      }
    }
  };

  useEffect(() => {
    if (subMode === "reviews" && selectedCourse) {
      handleFetchReviews();
    }
  }, [subMode, selectedCourse]);

  const handleDeleteReview = async () => {
    if (reviewToDelete) {
      try {
        await deleteReview(reviewToDelete);
        toast({ title: "ลบรีวิวสำเร็จ", description: "ลบข้อมูลรีวิวเรียบร้อยแล้ว" });
        handleFetchReviews(); // Refresh list
      } catch (error) {
        toast({ title: "เกิดข้อผิดพลาด", description: "ไม่สามารถลบรีวิวได้", variant: "destructive" });
      }
      setDialogType(null);
      setReviewToDelete(null);
    }
  };

  const handleConfirmEdit = async () => {
    if (editingCourse && selectedCourse) {
       try {
        await updateCourse(selectedCourse.course_id, editingCourse);
        toast({ title: "แก้ไขข้อมูลสำเร็จ", description: `อัปเดต ${editingCourse?.course_name_th}` });
        refetch();
       } catch (error) {
        toast({ title: "เกิดข้อผิดพลาด", description: "ไม่สามารถแก้ไขรายวิชาได้", variant: "destructive" });
       }
    }
    setDialogType(null);
    setSelectedCourse(null);
    setEditingCourse(null);
    setSubMode(null);
  };

  const handleConfirmDelete = async () => {
    if (selectedCourse) {
      try {
        await deleteCourse(selectedCourse.course_id);
        toast({ title: "ลบข้อมูลสำเร็จ", description: `ลบ ${selectedCourse?.course_name_th}` });
        refetch();
      } catch (error) {
         toast({ title: "เกิดข้อผิดพลาด", description: "ไม่สามารถลบรายวิชาได้", variant: "destructive" });
      }
    }
    setDialogType(null);
    setSelectedCourse(null);
    setEditingCourse(null);
    setSubMode(null);
  };

  const handleConfirmAdd = async () => {
    try {
      await addCourse(newCourse);
      toast({ title: "เพิ่มรายวิชาสำเร็จ", description: `เพิ่ม ${newCourse.course_name_th}` });
      refetch();
    } catch (error) {
       toast({ title: "เกิดข้อผิดพลาด", description: "ไม่สามารถเพิ่มรายวิชาได้ (รหัสวิชาอาจซ้ำ)", variant: "destructive" });
    }
    setDialogType(null);
    setNewCourse({
      course_id: "",
      course_name_th: "",
      credits: 3,
      faculty: "",
      category_64: "",
      competency_67: "",
      doc_type: "",
      description: "",
      clos: "",
    });
  };

  const isNewCourseValid = Object.values(newCourse).every((v) => v !== "" && v !== 0);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background">
      {/* Background gradient */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/10 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-border/50 backdrop-blur-md bg-background/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent-blue flex items-center justify-center">
              <span className="text-xl font-bold text-primary-foreground">A</span>
            </div>
            <span className="text-xl font-semibold text-foreground">Admin Panel</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-all"
          >
            <LogOut className="w-4 h-4" />
            ออกจากระบบ
          </button>
        </div>
      </header>

      <main className="relative z-10 container mx-auto px-4 py-8 max-w-4xl">
        {/* Mode selector */}
        <div className="flex gap-2 mb-8">
          <button
            onClick={() => { setMode("edit"); setSelectedCourse(null); }}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              mode === "edit"
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            <Edit3 className="w-4 h-4" />
            แก้ไข/ลบข้อมูล
          </button>
          <button
            onClick={() => { setMode("add"); setSelectedCourse(null); }}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              mode === "add"
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            <Plus className="w-4 h-4" />
            เพิ่มรายวิชา
          </button>
        </div>

        {/* Edit/Delete mode */}
        {mode === "edit" && (
          <div className="space-y-6 animate-fade-in">
            {/* Search */}
            <div className="relative">
               <label className="block text-sm font-medium text-foreground mb-2">
                 ค้นหารายวิชา
               </label>
               <CourseSearchInput
                  selectedCourse={selectedCourse}
                  onSelect={handleSelectCourse}
                  onClear={() => { setSelectedCourse(null); setEditingCourse(null); }}
                  courses={courses}
                />
            </div>

            {/* Selected course editor */}
            {selectedCourse && (
              <div className="animate-slide-up">
                {/* Sub-mode Selection */}
                {!subMode && (
                  <div className="glass-card p-6">
                     <div className="flex items-center justify-between mb-6">
                        <h2 className="text-lg font-semibold text-foreground">
                          จัดการรายวิชา: {selectedCourse.course_name_th}
                        </h2>
                        <button
                          onClick={() => { setSelectedCourse(null); setEditingCourse(null); }}
                          className="p-2 hover:bg-secondary rounded-lg transition-colors"
                        >
                          <X className="w-4 h-4 text-muted-foreground" />
                        </button>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <button
                          onClick={() => setSubMode("info")}
                          className="p-8 rounded-xl bg-secondary/30 hover:bg-secondary border border-border transition-all flex flex-col items-center justify-center gap-4 group"
                        >
                          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                            <Edit3 className="w-8 h-8 text-primary" />
                          </div>
                          <span className="font-medium text-lg">แก้ไขข้อมูลทั่วไป</span>
                          <span className="text-sm text-muted-foreground">หน่วยกิต, คำอธิบาย, หมวดหมู่</span>
                        </button>

                        <button
                          onClick={() => setSubMode("reviews")}
                          className="p-8 rounded-xl bg-secondary/30 hover:bg-secondary border border-border transition-all flex flex-col items-center justify-center gap-4 group"
                        >
                          <div className="w-16 h-16 rounded-full bg-accent-blue/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                             <MessageSquare className="w-8 h-8 text-primary" />
                          </div>
                          <span className="font-medium text-lg">จัดการรีวิว</span>
                          <span className="text-sm text-muted-foreground">ดูรายการรีวิว, ลบรีวิวที่ไม่เหมาะสม</span>
                        </button>
                      </div>
                  </div>
                )}
                
                {/* Edit Info Form */}
                {subMode === "info" && editingCourse && (
                  <CourseForm
                    course={editingCourse}
                    onChange={setEditingCourse}
                    onSave={() => setDialogType("edit")}
                    onDelete={() => setDialogType("delete")}
                    onCancel={() => setSubMode(null)}
                    mode="edit"
                  />
                )}
                
                {/* Manage Reviews Table */}
                {subMode === "reviews" && (
                   <div className="glass-card p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-lg font-semibold text-foreground">
                        จัดการรีวิว ({reviews.length})
                      </h2>
                      <button
                        onClick={() => setSubMode(null)}
                        className="text-sm text-muted-foreground hover:text-foreground underline"
                      >
                        ย้อนกลับ
                      </button>
                    </div>
                    
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left">
                        <thead className="text-xs text-muted-foreground uppercase bg-secondary/50">
                          <tr>
                            <th className="px-4 py-3 rounded-l-lg">ID</th>
                            <th className="px-4 py-3">เนื้อหารีวิว</th>
                            <th className="px-4 py-3 rounded-r-lg text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reviews.length === 0 ? (
                             <tr>
                                <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                                  ยังไม่มีรีวิวสำหรับวิชานี้
                                </td>
                             </tr>
                          ) : (
                            reviews.map((review) => (
                              <tr 
                                key={review.id} 
                                onClick={() => setViewReview(review)}
                                className="border-b border-border/50 hover:bg-secondary/30 transition-colors cursor-pointer"
                              >
                                <td className="px-4 py-3 font-mono text-muted-foreground">#{review.id}</td>
                                <td className="px-4 py-3">
                                  <div className="max-w-md truncate" title={review.review_content}>
                                    {review.review_content}
                                  </div>
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <button
                                    onClick={(e) => { 
                                      e.stopPropagation(); // Prevent row click
                                      setReviewToDelete(review.id); 
                                      setDialogType("deleteReview"); 
                                    }}
                                    className="p-2 text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                   </div>
                )}

              </div>
            )}
          </div>
        )}

        {/* Add mode */}
        {mode === "add" && (
           <CourseForm
             course={newCourse}
             onChange={setNewCourse}
             onSave={() => setDialogType("add")}
             mode="add"
             isValid={isNewCourseValid}
           />
        )}
      </main>

      {/* Confirmation dialogs */}
      <AlertDialog open={dialogType === "edit"} onOpenChange={() => setDialogType(null)}>
        <AlertDialogContent className="bg-card border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>ยืนยันการแก้ไข</AlertDialogTitle>
            <AlertDialogDescription>
              คุณต้องการบันทึกการแก้ไขข้อมูลรายวิชา {editingCourse?.course_name_th} ใช่หรือไม่?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={handleConfirmEdit} className="bg-primary text-primary-foreground">ยืนยัน</AlertDialogAction>
            <AlertDialogCancel className="bg-secondary text-foreground hover:bg-secondary/80">ยกเลิก</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={dialogType === "delete"} onOpenChange={() => setDialogType(null)}>
        <AlertDialogContent className="bg-card border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>ยืนยันการลบ</AlertDialogTitle>
            <AlertDialogDescription>
              คุณต้องการลบรายวิชา {selectedCourse?.course_name_th} ใช่หรือไม่? การกระทำนี้ไม่สามารถย้อนกลับได้
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={handleConfirmDelete} className="bg-destructive text-destructive-foreground">ลบ</AlertDialogAction>
            <AlertDialogCancel className="bg-secondary text-foreground hover:bg-secondary/80">ยกเลิก</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={dialogType === "deleteReview"} onOpenChange={() => setDialogType(null)}>
        <AlertDialogContent className="bg-card border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>ยืนยันการลบรีวิว</AlertDialogTitle>
            <AlertDialogDescription>
              คุณต้องการลบรีวิวนี้ใช่หรือไม่? การกระทำนี้ไม่สามารถย้อนกลับได้
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={handleDeleteReview} className="bg-destructive text-destructive-foreground">ลบ</AlertDialogAction>
            <AlertDialogCancel className="bg-secondary text-foreground hover:bg-secondary/80">ยกเลิก</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={dialogType === "add"} onOpenChange={() => setDialogType(null)}>
        <AlertDialogContent className="bg-card border-border">
          <AlertDialogHeader>
            <AlertDialogTitle>ยืนยันการเพิ่มรายวิชา</AlertDialogTitle>
            <AlertDialogDescription>
              คุณต้องการเพิ่มรายวิชา {newCourse.course_name_th} ใช่หรือไม่?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={handleConfirmAdd} className="bg-primary text-primary-foreground">ยืนยัน</AlertDialogAction>
            <AlertDialogCancel className="bg-secondary text-foreground hover:bg-secondary/80">ยกเลิก</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* View Review Dialog */}
      <Dialog open={!!viewReview} onOpenChange={(open) => !open && setViewReview(null)}>
        <DialogContent className="bg-card border-border sm:max-w-md">
          <DialogHeader>
            <DialogTitle>รายละเอียดรีวิว</DialogTitle>
            <DialogDescription>
              รหัสรีวิว: #{viewReview?.id}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-secondary/30 border border-border">
              <p className="text-foreground text-sm leading-relaxed whitespace-pre-wrap">
                {viewReview?.review_content}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
               <div>
                  <span className="font-semibold block mb-1">หมวดหมู่</span>
                  {viewReview?.category_64 || "-"}
               </div>
               <div>
                  <span className="font-semibold block mb-1">เครดิต</span>
                  {viewReview?.credits || "-"}
               </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Admin;
