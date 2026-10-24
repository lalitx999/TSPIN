import Link from "next/link";

export default function DoctorRegister() {
  return <main className="container py-5" style={{ maxWidth: 600 }}>
    <h1 className="h3">ขอบัญชีเจ้าหน้าที่คลินิก</h1>
    <p className="alert alert-warning">ไม่เปิดสมัครบัญชีเจ้าหน้าที่ด้วยตนเอง กรุณาติดต่อผู้ดูแลคลินิกเพื่อตรวจสอบตัวตนและกำหนดสิทธิ์ก่อนเข้าใช้งาน</p>
    <p>บัญชีเจ้าหน้าที่ไม่ใช่หลักฐานยืนยันใบอนุญาตแพทย์ และไม่ให้สิทธิ์ลงนามอนุมัติรายงานโดยอัตโนมัติ</p>
    <p>หากเคยใช้งานระบบเก่าแต่เข้าสู่ระบบไม่ได้ กรุณาให้ผู้ดูแลตรวจสอบบัญชี ไม่ต้องสมัครซ้ำ</p>
    <Link href="/doctor/login" className="btn btn-primary">กลับหน้าเข้าสู่ระบบ</Link>
  </main>;
}
