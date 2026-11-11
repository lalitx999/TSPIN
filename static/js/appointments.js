/*
 * ปฏิทินนัดหมาย (templates/patients/doctor_appointments.html)
 * ข้อมูลทั้งเดือนมากับหน้า: กดวันแล้วรายชื่อนัดแสดงด้านล่างทันที ไม่ต้องโหลดใหม่
 * สร้างนัด / เปลี่ยนสถานะ ส่งไป patients/views_appointments.py ตอบเป็น JSON
 */
(function () {
    'use strict';

    var DAY_NAMES = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์'];
    var STATUS_ORDER = { scheduled: 0, confirmed: 0, completed: 1, cancelled: 2 };

    function swal() {
        return window.Swal ? window.Swal.mixin({
            buttonsStyling: false, reverseButtons: true,
            customClass: { confirmButton: 'btn btn-primary', cancelButton: 'btn btn-light', actions: 'gap-2' },
        }) : null;
    }
    function fire(opts) {
        // ถ้ามีหน้าต่าง Bootstrap เปิดอยู่ ให้ SweetAlert อยู่ข้างใน ไม่งั้น focus trap ของ Bootstrap ดึงโฟกัสกลับ
        // ทำให้กด Enter / Tab ในหน้าต่างแจ้งเตือนไม่ได้
        opts = Object.assign({ target: document.querySelector('.modal.show') || document.body }, opts);
        var s = swal();
        if (s) return s.fire(opts);
        if (opts.showCancelButton) return Promise.resolve({ isConfirmed: window.confirm(opts.title) });
        window.alert([opts.title, opts.text].filter(Boolean).join('\n'));
        return Promise.resolve({ isConfirmed: true });
    }
    function esc(text) {
        var div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }
    function parseDay(iso) {
        var p = iso.split('-');
        return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    }

    window.apptCalendar = function (data) {
        return {
            weeks: data.weeks,
            month: data.month,
            today: data.today,
            selected: data.selected,
            appointments: data.appointments,
            months: data.months,
            slots: data.slots,
            urls: data.urls,

            // ฟอร์มสร้างนัด
            form: { patient: null, doctor_id: String(data.default_doctor || ''), date: '', time: '', notes: '' },
            query: '',
            results: [],
            active: 0,
            searching: false,
            searched: false,
            taken: [],
            patientTimes: [],
            invalid: [],
            saving: false,

            init: function () {
                var self = this;
                // แก้ช่องไหนแล้ว ให้กรอบแดงของช่องนั้นหายทันที
                [['form.doctor_id', 'doctor_id'], ['form.date', 'appointment_date'], ['form.time', 'appointment_time']].forEach(function (pair) {
                    self.$watch(pair[0], function () { self.invalid = self.invalid.filter(function (f) { return f !== pair[1]; }); });
                });
                // มาจากลิงก์ "นัดที่กำลังจะถึง" (#day-panel) ให้เลื่อนลงไปที่รายการของวันนั้น
                if (window.location.hash === '#day-panel') {
                    // รอให้เบราว์เซอร์คืนตำแหน่งเลื่อนเดิมหลัง reload ก่อน แล้วค่อยเลื่อนลงไปที่รายการของวัน
                    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';
                    setTimeout(function () { self.scrollToDay(); }, 150);
                }
            },

            // ---------- ปฏิทิน ----------
            inMonth: function (day) { return day.slice(0, 7) === this.month; },
            byDay: function (day) {
                return this.appointments
                    .filter(function (a) { return a.date === day; })
                    .sort(function (a, b) { return (STATUS_ORDER[a.status] - STATUS_ORDER[b.status]) || a.time.localeCompare(b.time); });
            },
            activeCount: function (day) {
                return this.appointments.filter(function (a) { return a.date === day && a.status !== 'cancelled'; }).length;
            },
            longDate: function (day) {
                if (!day) return '';
                var d = parseDay(day);
                return 'วัน' + DAY_NAMES[d.getDay()] + 'ที่ ' + d.getDate() + ' ' + this.months[d.getMonth()] + ' ' + (d.getFullYear() + 543);
            },
            dayCountLabel: function () {
                var list = this.byDay(this.selected);
                if (!list.length) return this.selected === this.today ? 'วันนี้' : '';
                var cancelled = list.filter(function (a) { return a.status === 'cancelled'; }).length;
                return (list.length - cancelled) + ' นัด' + (cancelled ? ' · ยกเลิก ' + cancelled : '') + (this.selected === this.today ? ' · วันนี้' : '');
            },
            pageUrl: function (day) {
                var params = new URLSearchParams(window.location.search);
                params.set('month', day.slice(0, 7));
                params.set('day', day);
                return '?' + params.toString() + '#day-panel';
            },
            pick: function (day) {
                if (!this.inMonth(day)) { window.location.href = this.pageUrl(day); return; }
                this.selected = day;
                var params = new URLSearchParams(window.location.search);
                params.set('month', this.month);
                params.set('day', day);
                window.history.replaceState(null, '', '?' + params.toString());
                this.scrollToDay();
            },
            scrollToDay: function () {
                var panel = document.getElementById('day-panel');
                if (!panel) return;
                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                panel.classList.remove('is-flash');
                void panel.offsetWidth;
                panel.classList.add('is-flash');
            },

            // ---------- เปลี่ยนสถานะ ----------
            setStatus: function (appt, status) {
                var self = this;
                var labels = { confirmed: 'ยืนยันนัด', completed: 'บันทึกว่ามาตรวจแล้ว', scheduled: 'กลับเป็นรอยืนยัน', cancelled: 'ยกเลิกนัด' };
                var ask = fire({
                    icon: status === 'cancelled' ? 'warning' : 'question',
                    title: labels[status] + '?',
                    html: '<strong>' + esc(appt.patient.name) + '</strong><br>' + esc(this.longDate(appt.date)) + ' เวลา ' + esc(appt.time) + ' น.',
                    showCancelButton: true, cancelButtonText: 'ไม่ใช่', confirmButtonText: labels[status],
                    focusCancel: status === 'cancelled',
                });
                ask.then(function (r) {
                    if (!r.isConfirmed) return;
                    var fd = new FormData();
                    fd.append('status', status);
                    self.post(appt.urls.status, fd).then(function (res) {
                        if (!res.ok) return fire({ icon: 'error', title: 'เปลี่ยนสถานะไม่สำเร็จ', text: res.error });
                        Object.assign(appt, res.appointment);
                        if (window.Swal) window.Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: labels[status] + 'แล้ว', showConfirmButton: false, timer: 2000 });
                    });
                });
            },

            // ---------- สร้างนัด ----------
            csrf: function () { return document.querySelector('input[name=csrfmiddlewaretoken]').value; },
            post: function (url, body) {
                return fetch(url, { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': this.csrf() } })
                    .then(function (r) { return r.json().catch(function () { return { ok: false, error: 'เซิร์ฟเวอร์ตอบกลับผิดพลาด (' + r.status + ')' }; }); })
                    .catch(function () { return { ok: false, error: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่' }; });
            },
            openCreate: function (day) {
                this.invalid = [];
                this.form.date = day && day >= this.today ? day : this.today;
                if (!this.form.time) this.form.time = '';
                this.loadTaken();
                bootstrap.Modal.getOrCreateInstance(this.$refs.modal).show();
                var self = this;
                this.$refs.modal.addEventListener('shown.bs.modal', function () {
                    var input = document.getElementById(self.form.patient ? 'apptDoctor' : 'apptPatient');
                    if (input) input.focus();
                }, { once: true });
            },
            search: function () {
                var self = this, q = this.query.trim();
                this.searched = false;
                if (!q) { this.results = []; return; }
                this.searching = true;
                fetch(this.urls.search + '?q=' + encodeURIComponent(q), { credentials: 'same-origin' })
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        if (self.query.trim() !== q) return;  // พิมพ์ต่อไปแล้ว ทิ้งผลเก่า
                        self.results = d.results || [];
                        self.active = 0;
                        self.searched = true;
                    })
                    .catch(function () { self.results = []; })
                    .finally(function () { self.searching = false; });
            },
            move: function (step) {
                if (!this.results.length) return;
                this.active = (this.active + step + this.results.length) % this.results.length;
            },
            choose: function (p) {
                this.form.patient = p;
                this.results = [];
                this.query = '';
                this.invalid = this.invalid.filter(function (f) { return f !== 'patient_id'; });
                this.loadTaken();
            },
            clearPatient: function () {
                this.form.patient = null;
                this.patientTimes = [];
                var self = this;
                this.$nextTick(function () { document.getElementById('apptPatient').focus(); });
            },
            loadTaken: function () {
                var self = this;
                this.taken = [];
                this.patientTimes = [];
                if (!this.form.date) return;
                var params = new URLSearchParams({ date: this.form.date, doctor: this.form.doctor_id || '', patient: this.form.patient ? this.form.patient.id : '' });
                fetch(this.urls.taken + '?' + params.toString(), { credentials: 'same-origin' })
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        self.taken = d.taken || [];
                        self.patientTimes = d.patient_times || [];
                        if (self.isTaken(self.form.time)) self.form.time = '';
                    })
                    .catch(function () {});
            },
            isTaken: function (t) { return !!t && this.taken.indexOf(t) !== -1; },
            isPastSlot: function (t) {
                if (this.form.date !== this.today) return false;
                var now = new Date();
                var hm = ('0' + now.getHours()).slice(-2) + ':' + ('0' + now.getMinutes()).slice(-2);
                return t < hm;
            },
            addTag: function (tag) {
                var notes = this.form.notes.trim();
                if (notes.indexOf(tag) !== -1) return;
                this.form.notes = notes ? notes + ', ' + tag : tag;
            },
            check: function () {
                var problems = [], bad = [];
                if (!this.form.patient) { problems.push('กรุณาเลือกคนไข้'); bad.push('patient_id'); }
                if (!this.form.doctor_id) { problems.push('กรุณาเลือกแพทย์ผู้ตรวจ'); bad.push('doctor_id'); }
                if (!this.form.date) { problems.push('กรุณาเลือกวันที่นัด'); bad.push('appointment_date'); }
                else if (this.form.date < this.today) { problems.push('ไม่สามารถนัดย้อนหลังได้'); bad.push('appointment_date'); }
                if (!this.form.time) { problems.push('กรุณาเลือกเวลานัด'); bad.push('appointment_time'); }
                this.invalid = bad;
                return problems;
            },
            submitCreate: function () {
                var self = this;
                var problems = this.check();
                if (problems.length) {
                    return fire({ icon: 'warning', title: 'ข้อมูลยังไม่ครบ', html: '<ul class="text-start mb-0">' + problems.map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul>', confirmButtonText: 'กลับไปแก้' });
                }
                var doctorSel = document.getElementById('apptDoctor');
                var doctorName = doctorSel.options[doctorSel.selectedIndex].text;
                var html = '<div class="text-start"><p class="mb-1"><strong>' + esc(this.form.patient.full_name) + '</strong> · HN ' + esc(this.form.patient.hn) + '</p>' +
                    '<p class="mb-1">' + esc(this.longDate(this.form.date)) + ' เวลา <strong>' + esc(this.form.time) + ' น.</strong></p>' +
                    '<p class="mb-0">แพทย์: ' + esc(doctorName) + (this.form.notes ? '<br>จุดประสงค์: ' + esc(this.form.notes) : '') + '</p></div>';
                fire({ icon: 'question', title: 'ยืนยันสร้างนัดหมาย?', html: html, showCancelButton: true, cancelButtonText: 'แก้ไข', confirmButtonText: 'สร้างนัด' })
                    .then(function (r) {
                        if (!r.isConfirmed) return;
                        var fd = new FormData();
                        fd.append('patient_id', self.form.patient.id);
                        fd.append('doctor_id', self.form.doctor_id);
                        fd.append('appointment_date', self.form.date);
                        fd.append('appointment_time', self.form.time);
                        fd.append('notes', self.form.notes);
                        self.saving = true;
                        self.post(self.urls.create, fd).then(function (res) {
                            self.saving = false;
                            if (!res.ok) {
                                self.invalid = res.fields || [];
                                var errs = res.errors || [res.error || 'บันทึกไม่สำเร็จ'];
                                return fire({ icon: 'error', title: 'สร้างนัดไม่สำเร็จ', html: '<ul class="text-start mb-0">' + errs.map(function (e) { return '<li>' + esc(e) + '</li>'; }).join('') + '</ul>' });
                            }
                            var day = res.appointment.date;
                            bootstrap.Modal.getOrCreateInstance(self.$refs.modal).hide();
                            fire({ icon: 'success', title: 'สร้างนัดหมายแล้ว', text: res.appointment.patient.name + ' · ' + self.longDate(day) + ' ' + res.appointment.time + ' น.', timer: 1800, showConfirmButton: false })
                                .then(function () {
                                    // ถ้า URL เดิมต่างแค่ #day-panel เบราว์เซอร์จะไม่โหลดใหม่ จึงสั่ง reload เอง
                                    window.history.replaceState(null, '', self.pageUrl(day));
                                    window.location.reload();
                                });
                        });
                    });
            },
        };
    };
})();
