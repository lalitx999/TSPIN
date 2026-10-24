import { NextResponse, type NextRequest } from 'next/server'

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // อนุญาตให้ผ่านหน้า login, register, และหน้าแรก
  const publicPaths = ['/', '/patient/login', '/patient/register', '/doctor/login']
  if (publicPaths.includes(pathname)) {
    return NextResponse.next()
  }

  // ป้องกัน path ที่ขึ้นต้นด้วย /patient และ /doctor
  // (การเช็ค auth จริงๆ ทำที่ client-side ด้วย Firebase Auth)
  if (pathname.startsWith('/patient') || pathname.startsWith('/doctor')) {
    // ปล่อยให้ผ่านไปก่อน client-side จะจัดการ redirect เอง
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
