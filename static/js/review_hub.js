/*
 * กล่องงานรอตรวจทาน (templates/patients/staff_review_queue.html)
 * - ข้อความอาการ: เขียน SOAP (ช่อง S ใส่ข้อความคนไข้ไว้ให้) -> ติ๊กตรวจทาน -> SweetAlert ยืนยัน -> บันทึกเข้าแฟ้ม
 * - ไม่เกี่ยวกับการรักษา: SweetAlert ถามเหตุผลก่อนปิดรายการ
 * - ถามจำนวนงานทุก 30 วินาที ถ้ามีงานเพิ่มขึ้นจะขึ้นแถบให้กดโหลดใหม่
 */
(function () {
    'use strict';

    var POLL_MS = 30000;

    function fire(opts) {
        opts = Object.assign({ target: document.querySelector('.modal.show') || document.body }, opts);
        if (!window.Swal) {
            if (opts.showCancelButton) return Promise.resolve({ isConfirmed: window.confirm(opts.title) });
            window.alert([opts.title, opts.text].filter(Boolean).join('\n'));
            return Promise.resolve({ isConfirmed: true });
        }
        return window.Swal.mixin({
            buttonsStyling: false, reverseButtons: true,
            customClass: { confirmButton: 'btn btn-primary', cancelButton: 'btn btn-light', actions: 'gap-2', input: 'form-control' },
        }).fire(opts);
    }
    function toast(title) {
        if (window.Swal) window.Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: title, showConfirmButton: false, timer: 2200 });
    }
    function esc(text) {
        var div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    window.reviewHub = function (config) {
        return {
            total: config.total,
            hasNew: false,
            current: null,
            soap: { subjective: '', objective: '', assessment: '', plan: '' },
            reviewed: false,
            saving: false,
            fields: [
                { name: 'subjective', tag: 'S', label: 'อาการที่คนไข้เล่า' },
                { name: 'objective', tag: 'O', label: 'สิ่งที่ตรวจพบ / ผลแล็บ' },
                { name: 'assessment', tag: 'A', label: 'การประเมิน' },
                { name: 'plan', tag: 'P', label: 'แผนการดูแล / ติดตาม' },
            ],

            init: function () {
                var self = this;
                setInterval(function () {
                    if (document.hidden) return;
                    fetch(config.pollUrl, { credentials: 'same-origin' })
                        .then(function (r) { return r.ok && !r.redirected ? r.json() : null; })
                        .then(function (d) { if (d && d.hub_total > self.total) self.hasNew = true; })
                        .catch(function () {});
                }, POLL_MS);
            },

            csrf: function () { return document.querySelector('input[name=csrfmiddlewaretoken]').value; },
            post: function (url, data) {
                var fd = new FormData();
                Object.keys(data).forEach(function (k) { fd.append(k, data[k]); });
                return fetch(url, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': this.csrf() } })
                    .then(function (r) { return r.json().catch(function () { return { status: 'error', message: 'เซิร์ฟเวอร์ตอบกลับผิดพลาด (' + r.status + ')' }; }); })
                    .catch(function () { return { status: 'error', message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่' }; });
            },
            removeRow: function (id) {
                var row = document.getElementById('item-' + id);
                if (row) row.remove();
                this.total = Math.max(0, this.total - 1);
                // ตัวนับบนแท็บและหัวข้อลดตามทันที
                document.querySelectorAll('[data-count="messages"], [data-count="all"]').forEach(function (el) {
                    el.textContent = Math.max(0, (parseInt(el.textContent, 10) || 0) - 1);
                });
            },

            openApprove: function (item) {
                var row = document.getElementById('item-' + item.id);
                var texts = row ? Array.prototype.map.call(row.querySelectorAll('.adm-bubble'), function (b) { return b.textContent.trim(); }) : [];
                this.current = item;
                this.soap = { subjective: texts.join('\n'), objective: '', assessment: '', plan: '' };
                this.reviewed = false;
                bootstrap.Modal.getOrCreateInstance(this.$refs.modal).show();
            },
            submitApprove: function () {
                var self = this, item = this.current;
                if (!this.soap.subjective.trim()) {
                    return fire({ icon: 'warning', title: 'กรุณากรอก S (อาการที่คนไข้เล่า)' });
                }
                var empty = this.fields.filter(function (f) { return !self.soap[f.name].trim(); }).map(function (f) { return f.tag; });
                fire({
                    icon: 'warning', title: 'บันทึกเข้าเวชระเบียน?', showCancelButton: true, cancelButtonText: 'กลับไปแก้', confirmButtonText: 'ยืนยันบันทึก', focusCancel: true,
                    html: '<strong>' + esc(item.name) + '</strong> · HN ' + esc(item.hn) +
                          (empty.length ? '<br><span class="text-danger small">ช่องที่ยังว่าง: ' + esc(empty.join(', ')) + '</span>' : '') +
                          '<br>บันทึกในชื่อของคุณ แก้ย้อนหลังไม่ได้',
                }).then(function (r) {
                    if (!r.isConfirmed) return;
                    self.saving = true;
                    self.post(item.url, Object.assign({ reviewed: '1' }, self.soap)).then(function (res) {
                        self.saving = false;
                        if (res.status !== 'ok') return fire({ icon: 'error', title: 'บันทึกไม่สำเร็จ', text: res.message });
                        bootstrap.Modal.getOrCreateInstance(self.$refs.modal).hide();
                        self.removeRow(item.id);
                        toast('บันทึกเข้าแฟ้ม ' + item.name + ' แล้ว');
                    });
                });
            },

            reject: function (item) {
                var self = this;
                fire({
                    icon: 'question', title: 'ไม่เกี่ยวกับการรักษา?',
                    html: 'ปิดรายการของ <strong>' + esc(item.name) + '</strong> โดยไม่บันทึกเข้าแฟ้ม',
                    input: 'select', inputOptions: {
                        'สอบถามสินค้า / ราคา / การสั่งซื้อ': 'สอบถามสินค้า / ราคา / การสั่งซื้อ',
                        'สอบถามเวลา / สถานที่ / นัดหมาย': 'สอบถามเวลา / สถานที่ / นัดหมาย',
                        'ข้อความซ้ำกับที่บันทึกไปแล้ว': 'ข้อความซ้ำกับที่บันทึกไปแล้ว',
                        'ระบบจับคำผิด ไม่ใช่เรื่องอาการ': 'ระบบจับคำผิด ไม่ใช่เรื่องอาการ',
                    },
                    inputPlaceholder: 'เลือกเหตุผล',
                    inputValidator: function (v) { return v ? null : 'กรุณาเลือกเหตุผล'; },
                    showCancelButton: true, cancelButtonText: 'ยกเลิก', confirmButtonText: 'ปิดรายการ',
                }).then(function (r) {
                    if (!r.isConfirmed) return;
                    self.post(item.url, { reason: r.value }).then(function (res) {
                        if (res.status !== 'ok') return fire({ icon: 'error', title: 'ปิดรายการไม่สำเร็จ', text: res.message });
                        self.removeRow(item.id);
                        toast('ปิดรายการแล้ว');
                    });
                });
            },
        };
    };
})();
