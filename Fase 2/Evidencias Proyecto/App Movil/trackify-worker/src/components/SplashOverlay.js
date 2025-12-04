// src/components/SplashOverlay.js
import React, { useEffect, useRef } from "react";
import { View, Animated, Easing, StyleSheet, Dimensions } from "react-native";

const { width } = Dimensions.get("window");

/** Ajusta aquí todas las duraciones para afinar la animación */
const TIMINGS = {
  introFade: 600,          // fade-in del contenedor
  popSpringFriction: 9,    // mayor = más lento (antes 6)
  rotateIn: 900,           // giro sutil
  subtitleDelay: 400,      // espera antes del subtítulo
  subtitleIn: 520,         // aparición del subtítulo (fade + slide-up)
  outroFade: 700,          // fade-out cuando ocultamos el splash
};

export default function SplashOverlay({ visible, onHidden }) {
  const opacity = useRef(new Animated.Value(1)).current;
  const scale   = useRef(new Animated.Value(0.88)).current;  // arranca un poco más pequeño
  const rotate  = useRef(new Animated.Value(0)).current;
  const subY    = useRef(new Animated.Value(14)).current;
  const subOp   = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Entrada: fade + pop suave + giro; luego subtítulo con slide-up
    Animated.sequence([
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 1,
          duration: TIMINGS.introFade,
          useNativeDriver: true,
          easing: Easing.out(Easing.cubic),
        }),
        Animated.spring(scale, {
          toValue: 1,
          friction: TIMINGS.popSpringFriction,
          tension: 80,
          useNativeDriver: true,
        }),
        Animated.timing(rotate, {
          toValue: 1,
          duration: TIMINGS.rotateIn,
          delay: 100,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
      ]),
      Animated.parallel([
        Animated.timing(subOp, {
          toValue: 1,
          duration: TIMINGS.subtitleIn,
          delay: TIMINGS.subtitleDelay,
          useNativeDriver: true,
        }),
        Animated.timing(subY, {
          toValue: 0,
          duration: TIMINGS.subtitleIn,
          delay: TIMINGS.subtitleDelay,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
      ]),
    ]).start();
  }, []);

  useEffect(() => {
    if (!visible) {
      Animated.timing(opacity, {
        toValue: 0,
        duration: TIMINGS.outroFade,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }).start(({ finished }) => finished && onHidden?.());
    }
  }, [visible]);

  const rotateDeg = rotate.interpolate({
    inputRange: [0, 1],
    outputRange: ["-3deg", "0deg"], // giro sutil
  });

  return (
    <Animated.View style={[styles.overlay, { opacity }]}>
      <View style={styles.bgTop} />
      <View style={styles.bgBottom} />
      <Animated.Image
        source={require("../../assets/logo.png")}
        resizeMode="contain"
        style={[styles.logo, { transform: [{ scale }, { rotate: rotateDeg }] }]}
      />
      <Animated.Text
        style={[styles.subtitle, { opacity: subOp, transform: [{ translateY: subY }] }]}
      >
        Gestión de Tareas y Desempeño
      </Animated.Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: "absolute",
    inset: 0,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fff",
  },
  bgTop: {
    position: "absolute",
    top: -width * 0.6,
    left: -width * 0.2,
    width: width * 1.4,
    height: width * 1.1,
    borderBottomLeftRadius: width,
    borderBottomRightRadius: width,
    backgroundColor: "#f5f7fb",
  },
  bgBottom: {
    position: "absolute",
    bottom: -width * 0.7,
    right: -width * 0.1,
    width: width * 1.3,
    height: width * 1.1,
    borderTopLeftRadius: width,
    borderTopRightRadius: width,
    backgroundColor: "#eef2f7",
  },
  logo: { width: 200, height: 200, marginBottom: 12 },
  subtitle: { fontSize: 14, color: "#4b5563", letterSpacing: 0.4 },
});
