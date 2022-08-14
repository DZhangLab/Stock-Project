package com.summer.stockproject.login.controller;

import com.summer.stockproject.login.Entity.User;
import com.summer.stockproject.login.service.RoleService;
import com.summer.stockproject.login.service.UserService;
import com.summer.stockproject.login.service.UserServiceImpl;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/login")
public class logingController {

    private UserService userService;
    private RoleService roleSerivce;

    @Autowired
    public logingController(UserService userService, RoleService roleSerivce) {
        this.userService = userService;
        this.roleSerivce = roleSerivce;
    }

    @GetMapping()
    public String loginView() {
//        System.out.println(userService.getReferenceById("harry"));
        User harrr = userService.getReferenceById("harry");
        System.out.println(harrr);
      //  System.out.println(roleSerivce.findAll());
        return "login/login";
    }

}
