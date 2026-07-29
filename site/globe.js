((root, factory) => {
  "use strict";

  const api = factory(root);
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.HubOptimusGlobe = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, (root) => {
  "use strict";

  const DEG = Math.PI / 180;
  const DEFAULT_CAMERA_DISTANCE = 3.25;

  function spherePoint(longitude, latitude, radius = 1) {
    const lambda = longitude * DEG;
    const phi = latitude * DEG;
    const cosPhi = Math.cos(phi);
    return [
      radius * cosPhi * Math.sin(lambda),
      radius * Math.sin(phi),
      radius * cosPhi * Math.cos(lambda)
    ];
  }

  function vectorLength([x, y, z]) {
    return Math.hypot(x, y, z);
  }

  function normalizeVector([x, y, z]) {
    const length = Math.hypot(x, y, z);
    if (length < 1e-12) return [0, 0, 1];
    return [x / length, y / length, z / length];
  }

  function greatCircle(start, end, segments = 96, lift = 0) {
    const a = spherePoint(start[0], start[1]);
    const b = spherePoint(end[0], end[1]);
    const dot = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2]));
    const omega = Math.acos(dot);
    const sinOmega = Math.sin(omega);
    const points = [];

    for (let index = 0; index <= segments; index += 1) {
      const amount = index / segments;
      let vector;
      if (Math.abs(sinOmega) < 1e-8) {
        vector = normalizeVector([
          a[0] + (b[0] - a[0]) * amount,
          a[1] + (b[1] - a[1]) * amount,
          a[2] + (b[2] - a[2]) * amount
        ]);
      } else {
        const fromWeight = Math.sin((1 - amount) * omega) / sinOmega;
        const toWeight = Math.sin(amount * omega) / sinOmega;
        vector = normalizeVector([
          a[0] * fromWeight + b[0] * toWeight,
          a[1] * fromWeight + b[1] * toWeight,
          a[2] * fromWeight + b[2] * toWeight
        ]);
      }

      const radius = 1 + lift * Math.sin(Math.PI * amount);
      points.push(vector.map((value) => value * radius));
    }

    return points;
  }

  function collectRings(geometry) {
    if (!geometry) return [];
    if (geometry.type === "Polygon") return geometry.coordinates;
    if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
    if (geometry.type === "GeometryCollection") {
      return geometry.geometries.flatMap(collectRings);
    }
    return [];
  }

  function extractRings(data) {
    if (!data || typeof data !== "object") return [];
    const geometries = data.type === "FeatureCollection"
      ? data.features.map((feature) => feature.geometry)
      : [data.geometry || data];
    return geometries.flatMap(collectRings);
  }

  function appendSegment(target, start, end, radius) {
    if (!Array.isArray(start) || !Array.isArray(end)) return;
    if (start.length < 2 || end.length < 2) return;
    const values = [start[0], start[1], end[0], end[1]];
    if (!values.every(Number.isFinite)) return;
    if (
      Math.abs(start[0]) > 180
      || Math.abs(end[0]) > 180
      || Math.abs(start[1]) > 90
      || Math.abs(end[1]) > 90
    ) return;
    target.push(...spherePoint(start[0], start[1], radius));
    target.push(...spherePoint(end[0], end[1], radius));
  }

  function lineSegmentsFromRings(rings, radius = 1.008) {
    const vertices = [];
    rings.forEach((ring) => {
      if (!Array.isArray(ring) || ring.length < 2) return;
      for (let index = 1; index < ring.length; index += 1) {
        appendSegment(vertices, ring[index - 1], ring[index], radius);
      }
      const first = ring[0];
      const last = ring[ring.length - 1];
      if (
        Array.isArray(first)
        && Array.isArray(last)
        && (first[0] !== last[0] || first[1] !== last[1])
      ) {
        appendSegment(vertices, last, first, radius);
      }
    });
    return new Float32Array(vertices);
  }

  function lineSegmentsFromPoints(lines) {
    const vertices = [];
    lines.forEach((line) => {
      for (let index = 1; index < line.length; index += 1) {
        vertices.push(...line[index - 1], ...line[index]);
      }
    });
    return new Float32Array(vertices);
  }

  function buildGraticule(radius = 1.003) {
    const lines = [];
    for (let latitude = -60; latitude <= 60; latitude += 30) {
      const line = [];
      for (let longitude = -180; longitude <= 180; longitude += 3) {
        line.push(spherePoint(longitude, latitude, radius));
      }
      lines.push(line);
    }
    for (let longitude = -150; longitude <= 180; longitude += 30) {
      const line = [];
      for (let latitude = -90; latitude <= 90; latitude += 3) {
        line.push(spherePoint(longitude, latitude, radius));
      }
      lines.push(line);
    }
    return lineSegmentsFromPoints(lines);
  }

  function buildSphere(latitudeBands = 64, longitudeBands = 96) {
    const positions = [];
    const normals = [];
    const indices = [];

    for (let latitudeIndex = 0; latitudeIndex <= latitudeBands; latitudeIndex += 1) {
      const latitude = -90 + (180 * latitudeIndex) / latitudeBands;
      for (let longitudeIndex = 0; longitudeIndex <= longitudeBands; longitudeIndex += 1) {
        const longitude = -180 + (360 * longitudeIndex) / longitudeBands;
        const point = spherePoint(longitude, latitude);
        positions.push(...point);
        normals.push(...point);
      }
    }

    const stride = longitudeBands + 1;
    for (let latitudeIndex = 0; latitudeIndex < latitudeBands; latitudeIndex += 1) {
      for (let longitudeIndex = 0; longitudeIndex < longitudeBands; longitudeIndex += 1) {
        const first = latitudeIndex * stride + longitudeIndex;
        const second = first + stride;
        indices.push(first, second, first + 1);
        indices.push(second, second + 1, first + 1);
      }
    }

    return {
      positions: new Float32Array(positions),
      normals: new Float32Array(normals),
      indices: new Uint16Array(indices)
    };
  }

  function identityMatrix() {
    return new Float32Array([
      1, 0, 0, 0,
      0, 1, 0, 0,
      0, 0, 1, 0,
      0, 0, 0, 1
    ]);
  }

  function multiplyMatrices(a, b) {
    const result = new Float32Array(16);
    for (let column = 0; column < 4; column += 1) {
      for (let row = 0; row < 4; row += 1) {
        result[column * 4 + row] =
          a[row] * b[column * 4]
          + a[4 + row] * b[column * 4 + 1]
          + a[8 + row] * b[column * 4 + 2]
          + a[12 + row] * b[column * 4 + 3];
      }
    }
    return result;
  }

  function rotationXMatrix(angle) {
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    return new Float32Array([
      1, 0, 0, 0,
      0, cosine, sine, 0,
      0, -sine, cosine, 0,
      0, 0, 0, 1
    ]);
  }

  function rotationYMatrix(angle) {
    const cosine = Math.cos(angle);
    const sine = Math.sin(angle);
    return new Float32Array([
      cosine, 0, -sine, 0,
      0, 1, 0, 0,
      sine, 0, cosine, 0,
      0, 0, 0, 1
    ]);
  }

  function translationMatrix(x, y, z) {
    const matrix = identityMatrix();
    matrix[12] = x;
    matrix[13] = y;
    matrix[14] = z;
    return matrix;
  }

  function perspectiveMatrix(fieldOfView, aspect, near, far) {
    const focalLength = 1 / Math.tan(fieldOfView / 2);
    const rangeInverse = 1 / (near - far);
    const result = new Float32Array(16);
    result[0] = focalLength / aspect;
    result[5] = focalLength;
    result[10] = (near + far) * rangeInverse;
    result[11] = -1;
    result[14] = near * far * 2 * rangeInverse;
    return result;
  }

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    if (!shader) throw new Error("WebGL could not create a shader");
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader) || "unknown shader error";
      gl.deleteShader(shader);
      throw new Error(`WebGL shader compilation failed: ${message}`);
    }
    return shader;
  }

  function createProgram(gl, vertexSource, fragmentSource) {
    const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
    const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
    const program = gl.createProgram();
    if (!program) throw new Error("WebGL could not create a program");
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const message = gl.getProgramInfoLog(program) || "unknown link error";
      gl.deleteProgram(program);
      throw new Error(`WebGL program linking failed: ${message}`);
    }
    return program;
  }

  function createArrayBuffer(gl, values) {
    const buffer = gl.createBuffer();
    if (!buffer) throw new Error("WebGL could not create a vertex buffer");
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, values, gl.STATIC_DRAW);
    return buffer;
  }

  function createElementBuffer(gl, values) {
    const buffer = gl.createBuffer();
    if (!buffer) throw new Error("WebGL could not create an index buffer");
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, values, gl.STATIC_DRAW);
    return buffer;
  }

  const SPHERE_VERTEX_SHADER = `
    attribute vec3 a_position;
    attribute vec3 a_normal;
    uniform mat4 u_model;
    uniform mat4 u_mvp;
    varying vec3 v_normal;

    void main() {
      v_normal = mat3(u_model) * a_normal;
      gl_Position = u_mvp * vec4(a_position, 1.0);
    }
  `;

  const SPHERE_FRAGMENT_SHADER = `
    precision mediump float;
    varying vec3 v_normal;

    void main() {
      vec3 normal = normalize(v_normal);
      vec3 light = normalize(vec3(-0.38, 0.62, 0.70));
      float diffuse = max(dot(normal, light), 0.0);
      float rim = pow(1.0 - max(normal.z, 0.0), 2.4);
      vec3 darkBlue = vec3(0.012, 0.055, 0.105);
      vec3 mediterranean = vec3(0.035, 0.235, 0.470);
      vec3 color = mix(darkBlue, mediterranean, 0.24 + diffuse * 0.62);
      color += vec3(0.055, 0.110, 0.180) * rim;
      gl_FragColor = vec4(color, 1.0);
    }
  `;

  const SIGNAL_VERTEX_SHADER = `
    attribute vec3 a_position;
    uniform mat4 u_mvp;
    uniform float u_point_size;

    void main() {
      gl_Position = u_mvp * vec4(a_position, 1.0);
      gl_PointSize = u_point_size;
    }
  `;

  const SIGNAL_FRAGMENT_SHADER = `
    precision mediump float;
    uniform vec4 u_color;
    uniform bool u_round_point;

    void main() {
      if (u_round_point) {
        vec2 point = gl_PointCoord - vec2(0.5);
        if (dot(point, point) > 0.25) discard;
      }
      gl_FragColor = u_color;
    }
  `;

  const ILLUSTRATIVE_POINTS = [
    [2.8457, 41.6999],
    [4.3517, 50.8503],
    [13.405, 52.52],
    [6.1432, 46.2044]
  ];

  const ILLUSTRATIVE_ROUTE_PAIRS = [
    [ILLUSTRATIVE_POINTS[0], ILLUSTRATIVE_POINTS[1]],
    [ILLUSTRATIVE_POINTS[0], ILLUSTRATIVE_POINTS[2]],
    [ILLUSTRATIVE_POINTS[1], ILLUSTRATIVE_POINTS[3]]
  ];

  function create(canvas) {
    if (!canvas || typeof canvas.getContext !== "function") return null;
    const gl = canvas.getContext("webgl", {
      alpha: true,
      antialias: true,
      depth: true,
      premultipliedAlpha: false
    });
    if (!gl) return null;

    const sphereProgram = createProgram(gl, SPHERE_VERTEX_SHADER, SPHERE_FRAGMENT_SHADER);
    const signalProgram = createProgram(gl, SIGNAL_VERTEX_SHADER, SIGNAL_FRAGMENT_SHADER);
    const sphere = buildSphere();
    const spherePositionBuffer = createArrayBuffer(gl, sphere.positions);
    const sphereNormalBuffer = createArrayBuffer(gl, sphere.normals);
    const sphereIndexBuffer = createElementBuffer(gl, sphere.indices);
    const graticule = buildGraticule();
    const graticuleBuffer = createArrayBuffer(gl, graticule);
    const routeLines = lineSegmentsFromPoints(
      ILLUSTRATIVE_ROUTE_PAIRS.map(([start, end]) => greatCircle(start, end, 96, 0.085))
    );
    const routeBuffer = createArrayBuffer(gl, routeLines);
    const nodePoints = new Float32Array(
      ILLUSTRATIVE_POINTS.flatMap(([longitude, latitude]) => (
        spherePoint(longitude, latitude, 1.022)
      ))
    );
    const nodeBuffer = createArrayBuffer(gl, nodePoints);
    let coastBuffer = null;
    let coastVertexCount = 0;
    let pixelRatio = 1;
    let destroyed = false;

    const sphereLocations = {
      position: gl.getAttribLocation(sphereProgram, "a_position"),
      normal: gl.getAttribLocation(sphereProgram, "a_normal"),
      model: gl.getUniformLocation(sphereProgram, "u_model"),
      mvp: gl.getUniformLocation(sphereProgram, "u_mvp")
    };
    const signalLocations = {
      position: gl.getAttribLocation(signalProgram, "a_position"),
      mvp: gl.getUniformLocation(signalProgram, "u_mvp"),
      color: gl.getUniformLocation(signalProgram, "u_color"),
      pointSize: gl.getUniformLocation(signalProgram, "u_point_size"),
      roundPoint: gl.getUniformLocation(signalProgram, "u_round_point")
    };

    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.clearDepth(1);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    function resize() {
      if (destroyed) return;
      const rect = canvas.getBoundingClientRect();
      const availableRatio = typeof root.devicePixelRatio === "number"
        ? root.devicePixelRatio
        : 1;
      pixelRatio = Math.min(Math.max(availableRatio, 1), 2);
      const width = Math.max(1, Math.round(rect.width * pixelRatio));
      const height = Math.max(1, Math.round(rect.height * pixelRatio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      gl.viewport(0, 0, width, height);
    }

    function loadGeography(data) {
      const rings = extractRings(data);
      if (!rings.length) throw new Error("Geographic data contains no polygon rings");
      const coastVertices = lineSegmentsFromRings(rings);
      if (!coastVertices.length) {
        throw new Error("Geographic data contains no renderable coastline segments");
      }
      if (coastBuffer) gl.deleteBuffer(coastBuffer);
      coastBuffer = createArrayBuffer(gl, coastVertices);
      coastVertexCount = coastVertices.length / 3;
    }

    function drawSignals(buffer, count, mode, mvp, color, pointSize = 1, round = false) {
      gl.useProgram(signalProgram);
      gl.uniformMatrix4fv(signalLocations.mvp, false, mvp);
      gl.uniform4fv(signalLocations.color, color);
      gl.uniform1f(signalLocations.pointSize, pointSize);
      gl.uniform1i(signalLocations.roundPoint, round ? 1 : 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(signalLocations.position);
      gl.vertexAttribPointer(signalLocations.position, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(mode, 0, count);
    }

    function draw({ rotation = -8, tilt = -11 } = {}) {
      if (destroyed) return;
      resize();
      const aspect = canvas.width / Math.max(canvas.height, 1);
      const projection = perspectiveMatrix(42 * DEG, aspect, 0.1, 10);
      const view = translationMatrix(0, 0, -DEFAULT_CAMERA_DISTANCE);
      const yaw = rotationYMatrix(rotation * DEG);
      const pitch = rotationXMatrix(tilt * DEG);
      const model = multiplyMatrices(pitch, yaw);
      const mvp = multiplyMatrices(projection, multiplyMatrices(view, model));

      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.disable(gl.BLEND);
      gl.enable(gl.CULL_FACE);

      gl.useProgram(sphereProgram);
      gl.uniformMatrix4fv(sphereLocations.model, false, model);
      gl.uniformMatrix4fv(sphereLocations.mvp, false, mvp);
      gl.bindBuffer(gl.ARRAY_BUFFER, spherePositionBuffer);
      gl.enableVertexAttribArray(sphereLocations.position);
      gl.vertexAttribPointer(sphereLocations.position, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, sphereNormalBuffer);
      gl.enableVertexAttribArray(sphereLocations.normal);
      gl.vertexAttribPointer(sphereLocations.normal, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, sphereIndexBuffer);
      gl.drawElements(gl.TRIANGLES, sphere.indices.length, gl.UNSIGNED_SHORT, 0);

      gl.enable(gl.BLEND);
      gl.disable(gl.CULL_FACE);
      drawSignals(
        graticuleBuffer,
        graticule.length / 3,
        gl.LINES,
        mvp,
        new Float32Array([0.24, 0.58, 0.92, 0.19])
      );
      if (coastBuffer && coastVertexCount) {
        drawSignals(
          coastBuffer,
          coastVertexCount,
          gl.LINES,
          mvp,
          new Float32Array([0.92, 0.91, 0.86, 0.76])
        );
      }
      drawSignals(
        routeBuffer,
        routeLines.length / 3,
        gl.LINES,
        mvp,
        new Float32Array([0.84, 0.64, 0.31, 0.72])
      );
      drawSignals(
        nodeBuffer,
        nodePoints.length / 3,
        gl.POINTS,
        mvp,
        new Float32Array([0.96, 0.72, 0.32, 0.92]),
        7 * pixelRatio,
        true
      );
    }

    function destroy() {
      if (destroyed) return;
      destroyed = true;
      [
        spherePositionBuffer,
        sphereNormalBuffer,
        sphereIndexBuffer,
        graticuleBuffer,
        routeBuffer,
        nodeBuffer,
        coastBuffer
      ].filter(Boolean).forEach((buffer) => gl.deleteBuffer(buffer));
      gl.deleteProgram(sphereProgram);
      gl.deleteProgram(signalProgram);
    }

    return Object.freeze({
      draw,
      loadGeography,
      resize,
      destroy
    });
  }

  return Object.freeze({
    create,
    geometry: Object.freeze({
      buildGraticule,
      buildSphere,
      collectRings,
      extractRings,
      greatCircle,
      lineSegmentsFromRings,
      perspectiveMatrix,
      spherePoint,
      vectorLength
    })
  });
});
