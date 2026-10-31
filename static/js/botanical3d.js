/*
 * ใบไม้เรืองแสง 3 มิติ (Botanical network) สำหรับหน้าแรก
 * ใบไม้ 1 ใบ: เส้นกลางใบ + เส้นใบแขนง 39 เส้น ปลายเส้นคือจุดของ 39 แกนชีววิทยา
 * มีละอองเซลล์ลอยรอบ ๆ หมุนช้า ๆ ลากเมาส์/นิ้วเพื่อหมุนได้
 * เขียนด้วย canvas 2D ล้วน (ไม่ใช้ไลบรารีภายนอก) และหยุดเคลื่อนไหวเมื่อผู้ใช้ตั้งค่าลดการเคลื่อนไหว
 */
(function () {
    'use strict';

    function init(canvas) {
        var ctx = canvas.getContext('2d');
        var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        var W = 0, H = 0, scale = 1;

        // ---------- สร้างรูปใบไม้ในพิกัด 3 มิติ (หน่วยประมาณ -1..1) ----------
        var LEN = 1.7;                       // ความยาวใบตามแกน y
        function halfWidth(t) {              // t: 0 (โคนใบ) .. 1 (ปลายใบ)
            return 0.62 * Math.pow(Math.sin(Math.PI * t), 0.85) * (1 - 0.25 * t);
        }
        function curl(x, t) {                // ใบไม้ห่อเล็กน้อยให้ดูเป็นสามมิติ
            return 0.22 * x * x - 0.12 * Math.sin(Math.PI * t);
        }
        function leafPoint(t, side) {        // side: -1 (ซ้าย) .. 1 (ขวา) ตามความกว้าง
            var x = side * halfWidth(t);
            var y = (t - 0.5) * LEN;
            return [x, y, curl(x, t)];
        }

        var outline = [], midrib = [], veins = [], nodes = [];
        for (var i = 0; i <= 80; i++) outline.push(leafPoint(i / 80, 1));
        for (var j = 80; j >= 0; j--) outline.push(leafPoint(j / 80, -1));
        for (var k = 0; k <= 40; k++) midrib.push(leafPoint(k / 40, 0));

        // 39 เส้นใบแขนง สลับซ้ายขวา โค้งขึ้นไปทางปลายใบ ปลายเส้น = จุดของแต่ละแกน
        for (var a = 0; a < 39; a++) {
            var side = a % 2 === 0 ? 1 : -1;
            var t0 = 0.08 + 0.84 * (a / 38);
            var reach = 0.78 + 0.18 * Math.sin(a * 1.7);
            var path = [];
            for (var s = 0; s <= 14; s++) {
                var u = s / 14;
                var t = Math.min(0.97, t0 + 0.16 * u * u);
                path.push(leafPoint(t, side * reach * u));
            }
            veins.push(path);
            nodes.push({ p: path[path.length - 1], phase: Math.random() * Math.PI * 2, axis: a + 1 });
        }

        // ละอองเซลล์/สปอร์ลอยรอบใบ
        var spores = [];
        for (var n = 0; n < 70; n++) {
            spores.push({
                p: [(Math.random() - 0.5) * 2.6, (Math.random() - 0.5) * 2.4, (Math.random() - 0.5) * 1.6],
                r: 0.6 + Math.random() * 1.8,
                drift: 0.0006 + Math.random() * 0.0012,
            });
        }

        // ---------- การหมุนและฉาย 3 มิติ -> 2 มิติ ----------
        var rotY = -0.5, rotX = 0.35, tilt = -0.35, dragging = false, lastX = 0, lastY = 0, velocity = 0.0025;

        function project(p) {
            var x = p[0], y = p[1], z = p[2];
            // เอียงใบ (หมุนรอบแกน z) ให้ดูเป็นธรรมชาติ
            var ct = Math.cos(tilt), st = Math.sin(tilt);
            var x0 = x * ct - y * st, y0 = x * st + y * ct;
            var cy = Math.cos(rotY), sy = Math.sin(rotY);
            var x1 = x0 * cy + z * sy, z1 = -x0 * sy + z * cy;
            var cx = Math.cos(rotX), sx = Math.sin(rotX);
            var y1 = y0 * cx - z1 * sx, z2 = y0 * sx + z1 * cx;
            var persp = 3.2 / (3.2 + z2);
            return [W / 2 + x1 * scale * persp, H / 2 - y1 * scale * persp, z2, persp];
        }

        function stroke(points, color, width) {
            ctx.beginPath();
            for (var i = 0; i < points.length; i++) {
                var q = project(points[i]);
                if (i === 0) ctx.moveTo(q[0], q[1]); else ctx.lineTo(q[0], q[1]);
            }
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.stroke();
        }

        function resize() {
            var rect = canvas.getBoundingClientRect();
            W = rect.width; H = rect.height;
            canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            scale = Math.min(W, H) * 0.42;
        }

        var time = 0;
        function draw() {
            ctx.clearRect(0, 0, W, H);

            // ละอองด้านหลัง
            for (var i = 0; i < spores.length; i++) {
                var sp = spores[i];
                if (!reduced) { sp.p[1] += sp.drift; if (sp.p[1] > 1.3) sp.p[1] = -1.3; }
                var q = project(sp.p);
                ctx.beginPath();
                ctx.arc(q[0], q[1], sp.r * q[3], 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(46,125,50,' + (0.10 + 0.12 * q[3]) + ')';
                ctx.fill();
            }

            // แผ่นใบ (ไล่เฉดเขียวโปร่งแสง)
            ctx.beginPath();
            for (var o = 0; o < outline.length; o++) {
                var qo = project(outline[o]);
                if (o === 0) ctx.moveTo(qo[0], qo[1]); else ctx.lineTo(qo[0], qo[1]);
            }
            ctx.closePath();
            var g = ctx.createLinearGradient(W * 0.3, H * 0.15, W * 0.7, H * 0.85);
            g.addColorStop(0, 'rgba(134, 239, 172, 0.30)');
            g.addColorStop(1, 'rgba(22, 101, 52, 0.22)');
            ctx.fillStyle = g;
            ctx.fill();
            ctx.strokeStyle = 'rgba(21, 128, 61, 0.55)';
            ctx.lineWidth = 1.6;
            ctx.stroke();

            // เส้นกลางใบและเส้นใบแขนง
            stroke(midrib, 'rgba(20, 83, 45, 0.70)', 2.4);
            for (var v = 0; v < veins.length; v++) stroke(veins[v], 'rgba(22, 101, 52, 0.42)', 1.1);

            // จุดของ 39 แกน (เรืองแสงเป็นจังหวะ เหมือนเซลล์มีชีวิต)
            var sorted = nodes.map(function (nd) { return { nd: nd, q: project(nd.p) }; })
                              .sort(function (a, b) { return a.q[2] - b.q[2]; });
            for (var s = 0; s < sorted.length; s++) {
                var nd = sorted[s].nd, qn = sorted[s].q;
                var pulse = reduced ? 0.5 : 0.5 + 0.5 * Math.sin(time * 0.04 + nd.phase);
                var r = (2.6 + 1.6 * pulse) * qn[3];
                var glow = ctx.createRadialGradient(qn[0], qn[1], 0, qn[0], qn[1], r * 4);
                glow.addColorStop(0, 'rgba(74, 222, 128, ' + (0.45 + 0.3 * pulse) + ')');
                glow.addColorStop(1, 'rgba(74, 222, 128, 0)');
                ctx.fillStyle = glow;
                ctx.beginPath(); ctx.arc(qn[0], qn[1], r * 4, 0, Math.PI * 2); ctx.fill();
                ctx.fillStyle = '#166534';
                ctx.beginPath(); ctx.arc(qn[0], qn[1], r, 0, Math.PI * 2); ctx.fill();
            }
        }

        function frame() {
            if (!dragging) rotY += velocity;
            time += 1;
            draw();
            if (!reduced) requestAnimationFrame(frame);
        }

        function pointer(e) { var t = e.touches ? e.touches[0] : e; return [t.clientX, t.clientY]; }
        canvas.addEventListener('pointerdown', function (e) { dragging = true; var p = pointer(e); lastX = p[0]; lastY = p[1]; });
        window.addEventListener('pointerup', function () { dragging = false; });
        window.addEventListener('pointermove', function (e) {
            if (!dragging) return;
            var p = pointer(e);
            rotY += (p[0] - lastX) * 0.008;
            rotX = Math.max(-1.0, Math.min(1.0, rotX + (p[1] - lastY) * 0.006));
            lastX = p[0]; lastY = p[1];
            if (reduced) draw();
        });
        window.addEventListener('resize', function () { resize(); draw(); });

        resize();
        if (reduced) draw(); else requestAnimationFrame(frame);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var canvases = document.querySelectorAll('canvas[data-botanical3d]');
        for (var i = 0; i < canvases.length; i++) init(canvases[i]);
    });
})();
