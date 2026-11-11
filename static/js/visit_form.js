/*
 * ฟอร์มบันทึกการตรวจในหน้าแฟ้มคนไข้ (templates/patients/partials/visit_form.html)
 * สัญญาณชีพ -> ซักประวัติ (พิมพ์ / ไมค์ถอดเสียงในเบราว์เซอร์ / กล้อง / อัปโหลด) -> Gemini สรุป SOAP -> ตรวจทาน -> เวชระเบียน
 * ร่างบันทึกอัตโนมัติที่เซิร์ฟเวอร์ (patients/views_visit.py) รีเฟรชหน้าแล้วทำต่อได้
 */
(function () {
    'use strict';

    var IMAGE_EDGE = 1600;      // ย่อรูปก่อนอัปโหลด ประหยัดเน็ตและพื้นที่
    var SAVE_DELAY = 1200;

    // SweetAlert2 ในสีของธีม (ปุ่มใช้คลาส Bootstrap ของระบบ)
    function swal() {
        if (!window.Swal) return null;
        return window.Swal.mixin({
            buttonsStyling: false,
            reverseButtons: true,
            customClass: { confirmButton: 'btn btn-primary', cancelButton: 'btn btn-light', denyButton: 'btn btn-light', actions: 'gap-2' },
        });
    }
    function alertBox(opts) {
        var s = swal();
        if (s) return s.fire(opts);
        window.alert([opts.title, opts.text].filter(Boolean).join('\n'));
        return Promise.resolve({ isConfirmed: true });
    }
    function confirmBox(opts) {
        var s = swal();
        if (s) return s.fire(Object.assign({ showCancelButton: true, cancelButtonText: 'ยกเลิก' }, opts));
        return Promise.resolve({ isConfirmed: window.confirm(opts.title) });
    }
    function toast(title) {
        if (!window.Swal) return;
        window.Swal.fire({ toast: true, position: 'top-end', icon: 'success', title: title, showConfirmButton: false, timer: 2200 });
    }
    function esc(text) {
        var div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }
    function listHtml(items) {
        return '<ul class="text-start mb-0">' + items.map(function (i) { return '<li>' + esc(i) + '</li>'; }).join('') + '</ul>';
    }

    // ย่อรูปด้านยาวไม่เกิน IMAGE_EDGE และแปลงเป็น JPEG (ถ้าเบราว์เซอร์อ่านไม่ได้ ส่งไฟล์เดิม)
    function shrinkImage(fileOrBlob) {
        return new Promise(function (resolve) {
            var url = URL.createObjectURL(fileOrBlob);
            var img = new Image();
            img.onload = function () {
                var scale = Math.min(1, IMAGE_EDGE / Math.max(img.naturalWidth, img.naturalHeight));
                var canvas = document.createElement('canvas');
                canvas.width = Math.round(img.naturalWidth * scale);
                canvas.height = Math.round(img.naturalHeight * scale);
                canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
                URL.revokeObjectURL(url);
                canvas.toBlob(function (blob) { resolve(blob || fileOrBlob); }, 'image/jpeg', 0.85);
            };
            img.onerror = function () { URL.revokeObjectURL(url); resolve(fileOrBlob); };
            img.src = url;
        });
    }

    window.visitForm = function (config) {
        var state = config.state || {};
        return {
            ranges: config.ranges,
            patient: config.patient,
            urls: config.urls,
            boxId: state.box_id || null,
            vitals: Object.assign({ bp_systolic: '', bp_diastolic: '', pulse: '', temperature: '', weight_kg: '', height_cm: '', spo2: '' }, state.vitals || {}),
            history: state.history_text || '',
            images: state.images || [],
            soap: Object.assign({ subjective: '', objective: '', assessment: '', plan: '' }, state.soap || {}),
            soapSource: state.soap_source || 'none',
            reviewed: false,
            invalid: [],
            busy: '',
            canManual: false,
            uploading: false,
            saveLabel: state.box_id ? 'มีร่างที่บันทึกไว้ ทำต่อได้เลย' : '',
            saveTimer: null,
            recording: false,
            interim: '',
            recognition: null,
            speechSupported: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
            stream: null,
            facing: 'environment',
            cameraCount: 0,

            vitalFields: [
                { name: 'bp_systolic', label: 'ความดันบน', unit: 'mmHg', step: '1', example: '120', col: 'col-6 col-md-3' },
                { name: 'bp_diastolic', label: 'ความดันล่าง', unit: 'mmHg', step: '1', example: '80', col: 'col-6 col-md-3' },
                { name: 'pulse', label: 'ชีพจร', unit: 'ครั้ง/นาที', step: '1', example: '72', col: 'col-6 col-md-3' },
                { name: 'temperature', label: 'อุณหภูมิ', unit: '°C', step: '0.1', example: '36.5', col: 'col-6 col-md-3' },
                { name: 'weight_kg', label: 'น้ำหนัก', unit: 'กก.', step: '0.1', example: '65', col: 'col-6 col-md-3' },
                { name: 'height_cm', label: 'ส่วนสูง', unit: 'ซม.', step: '0.5', example: '170', col: 'col-6 col-md-3' },
                { name: 'spo2', label: 'SpO2', unit: '%', step: '1', example: '98', col: 'col-6 col-md-3' },
            ],
            soapFields: [
                { name: 'subjective', tag: 'S', label: 'อาการที่ผู้ป่วยเล่า' },
                { name: 'objective', tag: 'O', label: 'สัญญาณชีพ / สิ่งที่ตรวจพบ / ผลแล็บ' },
                { name: 'assessment', tag: 'A', label: 'การประเมิน' },
                { name: 'plan', tag: 'P', label: 'แผนการดูแล / ตรวจเพิ่ม' },
            ],

            get soapUnlocked() { return this.soapSource === 'ai' || this.soapSource === 'manual'; },
            get bmi() {
                var w = parseFloat(this.vitals.weight_kg), h = parseFloat(this.vitals.height_cm);
                return (w > 0 && h > 0) ? (w / Math.pow(h / 100, 2)).toFixed(1) : '';
            },

            init: function () {
                var self = this;
                window.addEventListener('beforeunload', function () { if (self.saveTimer) self.save(); });
            },

            // ---------- คำขอไปเซิร์ฟเวอร์ ----------
            csrf: function () { return document.querySelector('#new-soap input[name=csrfmiddlewaretoken]').value; },
            payload: function (extra) {
                var fd = new FormData();
                if (this.boxId) fd.append('box_id', this.boxId);
                fd.append('history_text', this.history);
                for (var k in this.vitals) fd.append(k, this.vitals[k] == null ? '' : this.vitals[k]);
                if (this.soapUnlocked) {
                    fd.append('has_soap', '1');
                    for (var s in this.soap) fd.append(s, this.soap[s] || '');
                }
                for (var e in (extra || {})) fd.append(e, extra[e]);
                return fd;
            },
            post: function (url, body) {
                return fetch(url, { method: 'POST', body: body, credentials: 'same-origin', headers: { 'X-CSRFToken': this.csrf() } })
                    .then(function (r) {
                        return r.json().catch(function () { return { ok: false, error: 'เซิร์ฟเวอร์ตอบกลับผิดพลาด (' + r.status + ')' }; });
                    })
                    .catch(function () { return { ok: false, error: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่' }; });
            },

            // ---------- บันทึกร่างอัตโนมัติ ----------
            touch: function () {
                var self = this;
                this.saveLabel = 'กำลังพิมพ์…';
                clearTimeout(this.saveTimer);
                this.saveTimer = setTimeout(function () { self.save(); }, SAVE_DELAY);
            },
            save: function () {
                var self = this;
                clearTimeout(this.saveTimer);
                this.saveTimer = null;
                return this.post(this.urls.save, this.payload()).then(function (res) {
                    if (res.ok) {
                        self.boxId = res.box_id;
                        self.saveLabel = 'บันทึกร่างแล้ว ' + new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' }) + ' น.';
                    } else {
                        self.saveLabel = 'บันทึกร่างไม่สำเร็จ: ' + res.error;
                    }
                    return res;
                });
            },

            // ---------- ตรวจสัญญาณชีพในเบราว์เซอร์ก่อนส่ง (เซิร์ฟเวอร์ตรวจซ้ำ) ----------
            checkVitals: function () {
                var problems = [], bad = [];
                var self = this;
                this.vitalFields.forEach(function (f) {
                    var raw = self.vitals[f.name], range = self.ranges[f.name];
                    var value = parseFloat(raw);
                    if (raw === '' || raw == null) { problems.push('กรุณากรอก' + f.label); bad.push(f.name); }
                    else if (isNaN(value) || value < range[0] || value > range[1]) {
                        problems.push(f.label + ' ต้องอยู่ระหว่าง ' + range[0] + '–' + range[1] + ' ' + f.unit); bad.push(f.name);
                    }
                });
                var sys = parseFloat(this.vitals.bp_systolic), dia = parseFloat(this.vitals.bp_diastolic);
                if (!isNaN(sys) && !isNaN(dia) && dia >= sys) { problems.push('ความดันล่างต้องน้อยกว่าความดันบน'); bad.push('bp_diastolic'); }
                this.invalid = bad;
                return problems;
            },
            showVitalProblems: function (problems) {
                return alertBox({ icon: 'warning', title: 'สัญญาณชีพยังไม่ครบ', html: listHtml(problems), confirmButtonText: 'กลับไปกรอก' });
            },

            // ---------- ไมค์: ถอดเสียงภาษาไทยในเบราว์เซอร์ ----------
            toggleMic: function () { this.recording ? this.stopMic() : this.startMic(); },
            startMic: function () {
                var self = this;
                var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SR) return;
                var rec = new SR();
                rec.lang = 'th-TH';
                rec.continuous = true;
                rec.interimResults = true;
                rec.onresult = function (event) {
                    var interim = '';
                    for (var i = event.resultIndex; i < event.results.length; i++) {
                        var text = event.results[i][0].transcript;
                        if (event.results[i].isFinal) {
                            self.history = (self.history && !/\s$/.test(self.history) ? self.history + ' ' : self.history) + text.trim();
                            self.touch();
                        } else {
                            interim += text;
                        }
                    }
                    self.interim = interim;
                };
                rec.onerror = function (event) {
                    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                        self.recording = false;
                        alertBox({ icon: 'error', title: 'ใช้ไมค์ไม่ได้', text: 'กรุณาอนุญาตให้เว็บนี้ใช้ไมโครโฟนในเบราว์เซอร์ แล้วลองใหม่' });
                    }
                };
                // เบราว์เซอร์หยุดฟังเองเมื่อเงียบนาน: ถ้ายังไม่ได้กดหยุดให้ฟังต่อ
                rec.onend = function () {
                    self.interim = '';
                    if (self.recording) { try { rec.start(); } catch (e) { self.recording = false; } }
                };
                this.recognition = rec;
                this.recording = true;
                try { rec.start(); } catch (e) { this.recording = false; }
            },
            stopMic: function () {
                this.recording = false;
                this.interim = '';
                if (this.recognition) this.recognition.stop();
            },

            // ---------- รูป: อัปโหลด / ถ่าย ----------
            pickFiles: function (event) {
                var files = Array.prototype.slice.call(event.target.files || []);
                event.target.value = '';
                var self = this;
                files.reduce(function (chain, file) {
                    return chain.then(function () { return self.upload(file); });
                }, Promise.resolve());
            },
            upload: function (fileOrBlob) {
                var self = this;
                if (this.images.length >= 6) {
                    return alertBox({ icon: 'info', title: 'แนบรูปได้สูงสุด 6 รูป' });
                }
                this.uploading = true;
                return shrinkImage(fileOrBlob).then(function (blob) {
                    var type = blob.type || 'image/jpeg';
                    var fd = new FormData();
                    if (self.boxId) fd.append('box_id', self.boxId);
                    fd.append('image', blob, 'photo.' + (type.split('/')[1] || 'jpg'));
                    return self.post(self.urls.image, fd);
                }).then(function (res) {
                    self.uploading = false;
                    if (!res.ok) return alertBox({ icon: 'error', title: 'แนบรูปไม่สำเร็จ', text: res.error });
                    self.boxId = res.box_id;
                    self.images.push(res.image);
                });
            },
            removeImage: function (img) {
                var self = this;
                confirmBox({ icon: 'question', title: 'ลบรูปนี้ออกจากการซักประวัติ?', confirmButtonText: 'ลบรูป' }).then(function (r) {
                    if (!r.isConfirmed) return;
                    var fd = new FormData();
                    fd.append('box_id', self.boxId);
                    fd.append('media_id', img.media_id);
                    self.post(self.urls.imageRemove, fd).then(function (res) {
                        if (!res.ok) return alertBox({ icon: 'error', title: 'ลบรูปไม่สำเร็จ', text: res.error });
                        self.images = self.images.filter(function (i) { return i.media_id !== img.media_id; });
                    });
                });
            },
            openCamera: function () {
                var self = this;
                // ไม่มี getUserMedia (เช่น เปิดผ่าน http ที่ไม่ใช่ localhost): ใช้ช่องเลือกไฟล์ที่เปิดกล้องมือถือแทน
                if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) {
                    this.$refs.captureInput.click();
                    return;
                }
                var modal = bootstrap.Modal.getOrCreateInstance(this.$refs.cameraModal);
                this.$refs.cameraModal.addEventListener('hidden.bs.modal', function () { self.stopCamera(); }, { once: true });
                modal.show();
                navigator.mediaDevices.enumerateDevices().then(function (list) {
                    self.cameraCount = list.filter(function (d) { return d.kind === 'videoinput'; }).length;
                }).catch(function () {});
                this.startStream();
            },
            startStream: function () {
                var self = this;
                this.stopCamera();
                navigator.mediaDevices.getUserMedia({ video: { facingMode: this.facing, width: { ideal: 1920 } }, audio: false })
                    .then(function (stream) { self.stream = stream; self.$refs.video.srcObject = stream; })
                    .catch(function () {
                        bootstrap.Modal.getOrCreateInstance(self.$refs.cameraModal).hide();
                        alertBox({ icon: 'error', title: 'เปิดกล้องไม่ได้', text: 'กรุณาอนุญาตให้เว็บนี้ใช้กล้อง หรือกด "อัปโหลดรูป" แทน' });
                    });
            },
            switchCamera: function () {
                this.facing = this.facing === 'environment' ? 'user' : 'environment';
                this.startStream();
            },
            capture: function () {
                var video = this.$refs.video, self = this;
                if (!video.videoWidth) return;
                var canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                canvas.toBlob(function (blob) {
                    bootstrap.Modal.getOrCreateInstance(self.$refs.cameraModal).hide();
                    if (blob) self.upload(blob);
                }, 'image/jpeg', 0.9);
            },
            stopCamera: function () {
                if (this.stream) { this.stream.getTracks().forEach(function (t) { t.stop(); }); }
                this.stream = null;
            },

            // ---------- AI สรุป SOAP ----------
            summarize: function () {
                var self = this;
                var problems = this.checkVitals();
                if (problems.length) return this.showVitalProblems(problems);
                if (!this.history.trim() && !this.images.length) {
                    return alertBox({ icon: 'info', title: 'ยังไม่มีข้อมูลซักประวัติ', text: 'พิมพ์ พูด หรือแนบรูปอย่างน้อยหนึ่งอย่างก่อนให้ AI สรุป' });
                }
                var ask = this.soapSource === 'ai'
                    ? confirmBox({ icon: 'question', title: 'ให้ AI สรุปใหม่?', text: 'SOAP ที่แก้ไว้จะถูกแทนที่ด้วยร่างใหม่จาก AI', confirmButtonText: 'สรุปใหม่' })
                    : Promise.resolve({ isConfirmed: true });
                ask.then(function (r) {
                    if (!r.isConfirmed) return;
                    if (self.recording) self.stopMic();
                    self.busy = 'summarize';
                    if (window.Swal) {
                        window.Swal.fire({ title: 'AI กำลังสรุป SOAP', html: 'กำลังอ่านข้อความและรูป ใช้เวลาประมาณ 10–30 วินาที',
                            allowOutsideClick: false, didOpen: function () { window.Swal.showLoading(); } });
                    }
                    self.save().then(function () {
                        return self.post(self.urls.summarize, self.payload());
                    }).then(function (res) {
                        self.busy = '';
                        if (res.ok) {
                            self.soap = Object.assign({}, res.soap);
                            self.soapSource = 'ai';
                            self.reviewed = false;
                            alertBox({ icon: 'success', title: 'AI สรุปเรียบร้อย', text: 'กรุณาตรวจทานและแก้ไข SOAP ทุกช่องก่อนบันทึกเข้าเวชระเบียน', confirmButtonText: 'ไปตรวจทาน' })
                                .then(function () { document.getElementById('visit-step-3').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
                        } else if (res.errors) {
                            self.invalid = res.fields || [];
                            self.showVitalProblems(res.errors);
                        } else {
                            self.canManual = !!res.can_manual;
                            alertBox({ icon: 'error', title: 'AI สรุปไม่สำเร็จ', text: res.error });
                        }
                    });
                });
            },
            manualSoap: function () {
                var self = this;
                confirmBox({ icon: 'question', title: 'กรอก SOAP เอง?', text: 'ใช้เมื่อ AI สรุปไม่ได้ ระบบจะบันทึกว่า SOAP นี้ไม่ได้มาจาก AI', confirmButtonText: 'กรอกเอง' })
                    .then(function (r) {
                        if (!r.isConfirmed) return;
                        self.save().then(function () {
                            var fd = new FormData();
                            fd.append('box_id', self.boxId);
                            return self.post(self.urls.manual, fd);
                        }).then(function (res) {
                            if (res.ok) self.soapSource = 'manual';
                            else alertBox({ icon: 'error', title: 'เปิดช่อง SOAP ไม่สำเร็จ', text: res.error });
                        });
                    });
            },

            // ---------- บันทึกเข้าเวชระเบียน ----------
            commit: function () {
                var self = this;
                var problems = this.checkVitals();
                if (problems.length) return this.showVitalProblems(problems);
                var empty = this.soapFields.filter(function (f) { return !(self.soap[f.name] || '').trim(); }).map(function (f) { return f.tag; });
                var v = this.vitals;
                var html =
                    '<div class="text-start">' +
                    '<p class="mb-2"><strong>' + esc(this.patient.name) + '</strong> &middot; HN ' + esc(this.patient.hn) + '</p>' +
                    '<p class="mb-2 small">BP ' + esc(v.bp_systolic) + '/' + esc(v.bp_diastolic) + ' mmHg &middot; ชีพจร ' + esc(v.pulse) +
                    ' &middot; อุณหภูมิ ' + esc(v.temperature) + ' °C &middot; ' + esc(v.weight_kg) + ' กก. / ' + esc(v.height_cm) +
                    ' ซม. (BMI ' + esc(this.bmi) + ') &middot; SpO2 ' + esc(v.spo2) + '%</p>' +
                    (empty.length ? '<p class="text-danger small mb-2">ช่องที่ยังว่าง: ' + esc(empty.join(', ')) + '</p>' : '') +
                    '<p class="mb-0">ยืนยันว่าได้ตรวจทาน SOAP แล้ว และต้องการบันทึกเข้าเวชระเบียนในชื่อของคุณ</p></div>';
                confirmBox({ icon: 'warning', title: 'บันทึกเข้าเวชระเบียน?', html: html, confirmButtonText: 'ยืนยันบันทึก', focusCancel: true })
                    .then(function (r) {
                        if (!r.isConfirmed) return;
                        self.busy = 'commit';
                        self.post(self.urls.commit, self.payload({ reviewed: self.reviewed ? '1' : '0' })).then(function (res) {
                            self.busy = '';
                            if (!res.ok) {
                                if (res.errors) { self.invalid = res.fields || []; return self.showVitalProblems(res.errors); }
                                return alertBox({ icon: 'error', title: 'บันทึกไม่สำเร็จ', text: res.error });
                            }
                            var timeline = document.getElementById('soap-timeline');
                            var empty = document.getElementById('empty-soap-notice');
                            if (empty) empty.remove();
                            if (timeline) timeline.insertAdjacentHTML('afterbegin', res.html);
                            self.reset();
                            self.showNewSoap = false;
                            // แสดง Modal ตัวเลือกขั้นตอนถัดไป (วิเคราะห์ 39 แกนด้วย Copilot, จองนัด, หรือดูแฟ้มคนไข้)
                            var pid = res.patient_id || (self.patient && self.patient.id);
                            var nextUrlAxes = pid ? ('/clinical/axes/?patient_id=' + pid + '&auto_ai=1') : '/clinical/axes/';
                            var nextUrlAppt = pid ? ('/doctor/appointments/?patient_id=' + pid) : '/doctor/appointments/';
                            var modalHtml =
                                '<div class="text-center py-2">' +
                                '<p class="text-muted small mb-3">บันทึก SOAP และสัญญาณชีพของ <strong>' + esc(self.patient.name) + '</strong> เข้าเวชระเบียนเรียบร้อยแล้ว</p>' +
                                '<div class="d-flex flex-column gap-2 text-start">' +
                                '<a href="' + nextUrlAxes + '" class="btn btn-primary d-flex align-items-center justify-content-between p-2.5 text-decoration-none shadow-sm">' +
                                '<span><i class="fas fa-brain me-2"></i><strong>วิเคราะห์และประเมิน 39 แกนด้วย AI Copilot</strong></span>' +
                                '<i class="fas fa-arrow-right"></i>' +
                                '</a>' +
                                '<a href="' + nextUrlAppt + '" class="btn btn-outline-secondary d-flex align-items-center justify-content-between p-2.5 text-decoration-none">' +
                                '<span><i class="far fa-calendar-plus me-2"></i>สร้างใบนัดหมายตรวจติดตาม</span>' +
                                '<i class="fas fa-chevron-right"></i>' +
                                '</a>' +
                                '<button type="button" class="btn btn-light text-muted d-flex align-items-center justify-content-between p-2 mt-1" id="swal-stay-btn">' +
                                '<span><i class="fas fa-folder-open me-2"></i>เสร็จสิ้นการตรวจ (อยู่หน้าแฟ้มคนไข้)</span>' +
                                '</button>' +
                                '</div></div>';

                            var s = swal();
                            if (s) {
                                s.fire({
                                    icon: 'success',
                                    title: 'บันทึกเข้าเวชระเบียนแล้ว',
                                    html: modalHtml,
                                    showConfirmButton: false,
                                    showCancelButton: false,
                                    didOpen: function (modalEl) {
                                        var stayBtn = modalEl.querySelector('#swal-stay-btn');
                                        if (stayBtn) {
                                            stayBtn.addEventListener('click', function () {
                                                window.Swal.close();
                                                window.location.hash = 'soap-' + res.history_id;
                                                window.location.reload();
                                            });
                                        }
                                    }
                                });
                            } else {
                                window.location.hash = 'soap-' + res.history_id;
                                window.location.reload();
                            }
                        });
                    });
            },
            discard: function () {
                var self = this;
                confirmBox({ icon: 'warning', title: 'ทิ้งร่างนี้?', text: 'ข้อความซักประวัติ รูป และ SOAP ในร่างนี้จะหายจากฟอร์ม', confirmButtonText: 'ทิ้งร่าง' })
                    .then(function (r) {
                        if (!r.isConfirmed) return;
                        var fd = new FormData();
                        fd.append('box_id', self.boxId);
                        self.post(self.urls.discard, fd).then(function (res) {
                            if (!res.ok) return alertBox({ icon: 'error', title: 'ทิ้งร่างไม่สำเร็จ', text: res.error });
                            self.reset();
                            toast('ทิ้งร่างแล้ว');
                        });
                    });
            },
            reset: function () {
                if (this.recording) this.stopMic();
                clearTimeout(this.saveTimer);
                this.saveTimer = null;
                this.boxId = null;
                this.history = '';
                this.images = [];
                this.soap = { subjective: '', objective: '', assessment: '', plan: '' };
                this.soapSource = 'none';
                this.reviewed = false;
                this.invalid = [];
                this.canManual = false;
                this.saveLabel = '';
                for (var k in this.vitals) this.vitals[k] = '';
            },
        };
    };
})();
