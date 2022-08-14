package com.summer.stockproject.login.dao;

import com.summer.stockproject.login.Entity.Role;
import com.summer.stockproject.login.Entity.userrole;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RoleRepository extends JpaRepository<Role, userrole> {
}
