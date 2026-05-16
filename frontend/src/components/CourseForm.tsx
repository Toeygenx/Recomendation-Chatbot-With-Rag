import { Course } from "@/tpye/courses";
import { Save, Trash2, Plus } from "lucide-react";

interface CourseFormProps {
  course: Course;
  onChange: (updatedCourse: Course) => void;
  onSave: () => void;
  onDelete?: () => void;
  onCancel?: () => void;
  mode: "edit" | "add";
  isValid?: boolean;
}

const fields: { key: keyof Course; label: string; type?: string }[] = [
  { key: "course_id", label: "รหัสวิชา" },
  { key: "course_name_th", label: "ชื่อวิชา" },
  { key: "credits", label: "หน่วยกิต", type: "number" },
  { key: "faculty", label: "คณะต้นสังกัด" },
  { key: "category_64", label: "กลุ่มสาระ - 64" },
  { key: "competency_67", label: "สมรรถนะ - 67" },
  { key: "doc_type", label: "doc_type" },
  { key: "description", label: "description" },
  { key: "clos", label: "CLOs" },
];

const CourseForm = ({ 
  course, 
  onChange, 
  onSave, 
  onDelete, 
  onCancel, 
  mode, 
  isValid = true 
}: CourseFormProps) => {

  const handleChange = (key: keyof Course, value: string | number) => {
    // strict limit for course_id
    if (key === "course_id") {
      const strVal = String(value);
      if (strVal.length > 8) return;
      if (!/^\d*$/.test(strVal)) return; // Allow numbers only
    }
    onChange({ ...course, [key]: value });
  };

  return (
    <div className="glass-card p-6 animate-fade-in">
      {mode === "add" ? (
         <h2 className="text-lg font-semibold text-foreground mb-6">เพิ่มรายวิชาใหม่</h2>
      ) : (
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-foreground">
            แก้ไขข้อมูลรายวิชา
          </h2>
          {onCancel && (
            <button
              onClick={onCancel}
              className="text-sm text-muted-foreground hover:text-foreground underline"
            >
              ย้อนกลับ
            </button>
          )}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {fields.map((field) => (
          <div key={field.key} className={field.key === "description" || field.key === "clos" ? "md:col-span-2" : ""}>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              {field.label} {mode === "add" && <span className="text-destructive">*</span>}
            </label>
            {field.key === "description" || field.key === "clos" ? (
              <textarea
                value={course[field.key]}
                onChange={(e) => handleChange(field.key, e.target.value)}
                rows={2}
                className="w-full bg-secondary/50 border border-border rounded-lg p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
              />
            ) : (
              <input
                type={field.type || "text"}
                value={course[field.key]}
                onChange={(e) =>
                  handleChange(
                    field.key,
                    field.type === "number" ? Number(e.target.value) : e.target.value
                  )
                }
                disabled={field.key === "course_id" && mode === "edit"}
                className={`w-full bg-secondary/50 border border-border rounded-lg p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed`}
              />
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-3 mt-6">
        {mode === "add" ? (
           <button
             onClick={onSave}
             disabled={!isValid}
             className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-primary to-accent-blue text-primary-foreground font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
           >
             <Plus className="w-4 h-4" />
             เพิ่มรายวิชา
           </button>
        ) : (
          <>
            <button
              onClick={onSave}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl bg-primary text-primary-foreground font-medium hover:opacity-90 transition-all"
            >
              <Save className="w-4 h-4" />
              บันทึกการแก้ไข
            </button>
            {onDelete && (
              <button
                onClick={onDelete}
                className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-destructive text-destructive-foreground font-medium hover:opacity-90 transition-all"
              >
                <Trash2 className="w-4 h-4" />
                ลบ
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default CourseForm;
